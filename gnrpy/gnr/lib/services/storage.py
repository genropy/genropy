#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


import os
import re
import random
import os
import shutil
import mimetypes
from paste import fileapp
from paste.httpheaders import ETAG
from subprocess import check_call, check_output
import stat

from gnr.core.gnrsys import expandpath
from gnr.core import gnrstring
from gnr.core.gnrbag import Bag, BagResolver
from gnr.lib.services import GnrBaseService, BaseServiceType

class NotExistingStorageNode(Exception):
    pass

import sys
from collections import deque


class ExitStack(object):
    """Context manager for dynamic management of a stack of exit callbacks

    For example:

        with ExitStack() as stack:
            files = [stack.enter_context(open(fname)) for fname in filenames]
            # All opened files will automatically be closed at the end of
            # the with statement, even if attempts to open files later
            # in the list raise an exception

    """
    def __init__(self):
        self._exit_callbacks = deque()

    def pop_all(self):
        """Preserve the context stack by transferring it to a new instance"""
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = deque()
        return new_stack

    def _push_cm_exit(self, cm, cm_exit):
        """Helper to correctly register callbacks to __exit__ methods"""
        def _exit_wrapper(*exc_details):
            return cm_exit(cm, *exc_details)
        _exit_wrapper.__self__ = cm
        self.push(_exit_wrapper)

    def push(self, exit):
        """Registers a callback with the standard __exit__ method signature

        Can suppress exceptions the same way __exit__ methods can.

        Also accepts any object with an __exit__ method (registering a call
        to the method instead of the object itself)
        """
        # We use an unbound method rather than a bound method to follow
        # the standard lookup behaviour for special methods
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__exit__
        except AttributeError:
            # Not a context manager, so assume its a callable
            self._exit_callbacks.append(exit)
        else:
            self._push_cm_exit(exit, exit_method)
        return exit # Allow use as a decorator

    def callback(self, callback, *args, **kwds):
        """Registers an arbitrary callback and arguments.

        Cannot suppress exceptions.
        """
        def _exit_wrapper(exc_type, exc, tb):
            callback(*args, **kwds)
        # We changed the signature, so using @wraps is not appropriate, but
        # setting __wrapped__ may still help with introspection
        _exit_wrapper.__wrapped__ = callback
        self.push(_exit_wrapper)
        return callback # Allow use as a decorator

    def enter_context(self, cm):
        """Enters the supplied context manager

        If successful, also pushes its __exit__ method as a callback and
        returns the result of the __enter__ method.
        """
        # We look up the special methods on the type to match the with statement
        _cm_type = type(cm)
        _exit = _cm_type.__exit__
        result = _cm_type.__enter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    def close(self):
        """Immediately unwind the context stack"""
        self.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        # We manipulate the exception state so it behaves as though
        # we were actually nesting multiple with statements
        frame_exc = sys.exc_info()[1]
        def _fix_exception_context(new_exc, old_exc):
            while 1:
                exc_context = new_exc.__context__
                if exc_context in (None, frame_exc):
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        # Callbacks are invoked in LIFO order to match the behaviour of
        # nested context managers
        suppressed_exc = False
        while self._exit_callbacks:
            cb = self._exit_callbacks.pop()
            try:
                if cb(*exc_details):
                    suppressed_exc = True
                    exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                # simulate the stack of exceptions by setting the context
                _fix_exception_context(new_exc_details[1], exc_details[1])
                if not self._exit_callbacks:
                    raise
                exc_details = new_exc_details
        return suppressed_exc
class LocalPath(object):
    def __init__(self, fullpath=None):
        self.fullpath = fullpath

    def __enter__(self):
        return self.fullpath

    def __exit__(self, exc, value, tb):
        pass


class ServiceType(BaseServiceType):
    
    def conf_home(self):
        return dict(implementation='local',base_path=self.site.site_static_dir)

    def conf_mail(self):
        return dict(implementation='local',base_path='%s/mail' %self.site.site_static_dir)

    def conf_site(self):
        return dict(implementation='local',base_path=self.site.site_static_dir)

    def conf_rsrc(self):
        return dict(implementation='symbolic')

    def conf_pkg(self):
        return dict(implementation='symbolic')

    def conf_dojo(self):
        return dict(implementation='symbolic')

    def conf_conn(self):
        return dict(implementation='symbolic')

    def conf_page(self):
        return dict(implementation='symbolic')

    def conf_temp(self):
        return dict(implementation='symbolic')

    def conf_gnr(self):
        return dict(implementation='symbolic')

    def conf_pages(self):
        return dict(implementation='symbolic')

    def conf_user(self):
        return dict(implementation='symbolic')
    
    def conf__raw_(self):
        return dict(implementation='raw')

    def conf__http_(self):
        return dict(implementation='http')

    #def conf_vol(self):
    #    return dict(implementation='symbolic')
    def getServiceFactory(self,implementation=None):
        return self.implementations.get(implementation)
    
class BaseStorageNode(object):
    """Base class for storage nodes.

    This base class will allow different implementations of storage nodes
    (legacy and new genro-storage based) while maintaining a common interface.
    """
    pass


class LegacyStorageNode(BaseStorageNode):
    def __str__(self):
        return 'StorageNode %s <%s>' %(self.service.service_implementation,self.internal_path)

    def __init__(self, parent=None, path=None, service=None, autocreate=None,must_exist=False, version=None,mode='r'):
        self.service = service
        self.parent = parent
        self.path = self.service.expandpath(path)
        if must_exist and not self.service.exists(self.path):
            raise NotExistingStorageNode
        self.mode = mode
        self.autocreate = autocreate
        self.version = version

    @property
    def versions(self):
        return self.service.versions(self.path)

    @property
    def md5hash(self):
        """Returns the md5 hash"""
        return self.service.md5hash(self.path)

    @property
    def fullpath(self):
        """Returns the full symbolic path (eg. storage:path/to/me)"""
        return self.service.fullpath(self.path)

    @property
    def ext(self):
        """Returns the file extension without leading dots"""
        return self.service.extension(self.path)

    @property
    def isdir(self):
        """Returns True if the StorageNode points to a directory"""
        return self.service.isdir(self.path)

    def children(self):
        """Returns a list of StorageNodes cointained (if self.isdir)"""
        if self.isdir:
            return self.service.children(self.path)

    def listdir(self):
        """Returns a list of file/dir names cointained (if self.isdir)"""
        if self.isdir:
            return self.service.listdir(self.path)
    
    def mkdir(self, *args):
        """Creates me as a directory"""
        return self.service.mkdir(self.path, *args)

    @property
    def internal_path(self, **kwargs):
        return self.service.internal_path(self.path)

    @property
    def basename(self, **kwargs):
        """Returns the base name (eg. self.path=="/path/to/me.txt" self.basename=="me.txt")"""
        return self.service.basename(self.path)

    @property
    def cleanbasename(self, **kwargs):
        """Returns the basename without extension"""
        return os.path.splitext(self.service.basename(self.path))[0]

    @property
    def isfile(self):
        """Returns True if the StorageNode points to a file"""
        return self.service.isfile(self.path) 

    @property
    def exists(self):
        """Returns True if the StorageNode points to an existing file/dir"""
        return self.service.exists(self.path)
    
    @property
    def mtime(self):
        """Returns the last modification timestamp"""
        return self.service.mtime(self.path)

    @property
    def ext_attributes(self):
        """Returns the file size (if self.isfile)"""
        return self.service.ext_attributes(self.path)

    @property
    def size(self):
        """Returns the file size (if self.isfile)"""
        return self.service.size(self.path)
    
    @property
    def dirname(self):
        """Returns the fullpath of parent directory"""
        return '%s:%s'%(self.service.service_name,os.path.dirname(self.path))
        
    @property
    def parentStorageNode(self):
        """Returns the StorageNode pointing to the parent directory"""
        return self.parent.storageNode(self.dirname)
    
    def splitext(self):
        """Returns a tuple of filename and extension"""
        return os.path.splitext(self.path)

    def base64(self, mime=None):
        """Returns the base64 encoded string of the file content"""
        return self.service.base64(self.path, mime=mime)

    def open(self, mode='rb'):
        """Is a context manager that returns the open file pointed"""
        self.service.autocreate(self.path, autocreate=-1)
        kwargs = {'mode':mode}
        if self.version and self.service.is_versioned:
            kwargs['version_id'] = self.version
        return self.service.open(self.path,**kwargs)

    def url(self, **kwargs):
        """Returns the external url of this file"""
        return self.service.url(self.path, **kwargs)

    def internal_url(self, **kwargs):
        return self.service.internal_url(self.path, **kwargs)

    def delete(self):
        """Deletes the dir content"""
        return self.service.delete(self.path)

    def move(self, dest=None):
        """Moves the pointed file to another path, self now points to the new location"""
        dest = self.service.move(source=self, dest=dest)
        self.path = dest.path
        self.service = dest.service

    def copy(self, dest=None):
        """Copy self to another path"""
        return self.service.copy(source=self, dest=dest)

    def serve(self, environ, start_response, **kwargs):
        """Serves the file content"""
        return self.service.serve(self.path, environ, start_response, **kwargs)

    def local_path(self, mode=None, keep=False):
        """Is a context manager that return a local path to a temporary file 
        with the pointed file content, if modified, the new content will replace
        the original content. Useful to let an external process work on a file
        stored in cloud (like in a s3 bucket)"""
        self.service.autocreate(self.path, autocreate=-1)
        return self.service.local_path(self.path, mode=mode or self.mode, keep=keep)

    def child(self, path=None):
        """Returns a StorageNode pointing a sub path"""
        if self.path and self.path[-1]!='/':
            path = '/%s'%path
        return self.service.parent.storageNode('%s%s'%(self.fullpath,path))

    @property
    def mimetype(self):
        """Returns the file mime type"""
        return self.service.mimetype(self.path)

    def get_metadata(self):
        """Returns the file metadata"""
        return self.service.get_metadata(self.path)

    def set_metadata(self, metadata):
        """Sets the file metadata"""
        self.service.set_metadata(self.path, metadata)

    def fill_from_url(self, url):
        import urllib.request
        with self.open('wb') as me:
            with urllib.request.urlopen(url) as response:
                me.write(response.read())

class StorageService(GnrBaseService):

    def _getNode(self, node=None):
        return node if isinstance(node, StorageNode) else self.parent.storageNode(node)

    def internal_path(self, *args, **kwargs):
        pass

    def md5hash(self,*args):
        """Returns the md5 hash of a given path"""
        pass

    def versions(self,*args):
        return []

    def fullpath(self, path):
        """Returns the fullpath (comprending self.service_name) of a path"""
        return "%s:%s"%(self.service_name, path)

    def local_path(self, *args, **kwargs):
        """Is a context manager that copies locally a remote file in a temporary
        file and, if modified, at the __exit__ copies back on remote.
        If on localfile works directly with the original file"""
        pass
    
    def expandpath(self,path):
        return path

    def basename(self, path=None):
        """Returns the basename of a path"""
        return self.split_path(path)[-1]
    
    def extension(self, path=None):
        """Returns the extension without the leading dots"""
        basename = self.basename(path)
        return os.path.splitext(basename)[-1].strip('.')

    def split_path(self, path):
        """Splits the path to a list"""
        return path.replace('/','\t').replace(os.path.sep,'/').replace('\t','/').split('/')

    def sync_to_service(self, dest_service, subpath='', skip_existing=True, skip_same_size=False,
        thermo=None, done_list=None, doneCb=None):
        """Copies the service content to another service"""
        assert not (skip_existing and skip_same_size), 'use either skip_existing or skip_same_size'
        done_list = done_list or []
        storage_resolver = StorageResolver(self.parent.storageNode('%s:%s'%(self.service_name,subpath)))
        to_copy = []
        def checkSync(node):
            if node.attr.get('file_ext') == 'directory':
                return
            fullpath = node.attr.get('abs_path')
            if fullpath in done_list:
                return
            src_node = self.parent.storageNode(fullpath)
            rel_path = fullpath.replace('%s:'%self.service_name,'',1)
            dest_node = self.parent.storageNode('%s:%s'%(dest_service,rel_path))
            if skip_existing or skip_same_size:
                if dest_node.exists:
                    size = dest_node.size if skip_same_size else node.attr.get('size')
                    if size == node.attr.get('size')==dest_node.size:
                        return

            to_copy.append((src_node, dest_node))
        storage_resolver().walk(checkSync, _mode='')
        to_copy = thermo(to_copy) if thermo else to_copy
        for srcNode, destNode in to_copy:
            self.copy(srcNode, destNode)
            if doneCb:
                doneCb(srcNode)

    def mimetype(self, *args,**kwargs):
        """Returns the mimetype of file at the given path"""
        return mimetypes.guess_type(self.internal_path(*args))[0] or 'application/octet-stream'

    def base64(self, *args, **kwargs):
        """Convert a file (specified by a path) into a data URI."""
        import base64
        if not self.exists(*args):
            return u''
        mime = kwargs.get('mime', False)
        if mime is True:
            mime = self.mimetype(*args)
        with self.open(*args, mode='rb') as fp:
            data = fp.read()
            data64 = base64.b64encode(data).decode()
            if mime:
                result  ='data:%s;base64,%s' % (mime, data64)
            else:
                result = '%s' % data64
            return result

    def internal_url(self, *args, **kwargs):
        external_host = self.parent.external_host.rstrip('/')
        outlist = [external_host, '_storage', self.service_name]
        outlist.extend(args)
        url = '/'.join(outlist)
        if not kwargs:
            return url
        nocache = kwargs.pop('nocache', None)
        if nocache:
            if self.exists(*args):
                mtime = self.mtime(*args)
            else:
                mtime = random.random() * 100000
            kwargs['mtime'] = '%0.0f' % (mtime)

        url = '%s?%s' % (url, '&'.join(['%s=%s' % (k, v) for k, v in list(kwargs.items())]))
        return url

    @property
    def is_versioned(self):
        return False

    @property
    def location_identifier(self):
        pass

    def open(self,*args,**kwargs):
        """Is a context manager that returns the open file at given path"""
        pass

    def url(self,*args, **kwargs):
        """Returns the external url of path"""
        pass

    def symbolic_url(self,*args, **kwargs):
        pass

    def mtime(self, *args):
        """Return the last modification time of file at a path"""
        pass

    def size(self, *args):
        """Return the size of a file at a path"""
        pass

    def delete(self, *args):
        """Deletes the file or the directory"""
        if not self.exists(*args):
            return
        if self.isdir(*args):
            self.delete_dir(*args)
        else:
            self.delete_file(*args)


    def autocreate(self, *args, **kwargs):
        """Autocreates all intermediate directories of a path"""

        autocreate=kwargs.pop('autocreate', None)
        if not autocreate:
            return
        args = self.split_path('/'.join(args))
        if autocreate != True:
            autocreate_args = args[:autocreate]
        else:
            autocreate_args = args
        
        dest_dir = LegacyStorageNode(parent=self.parent,
            service=self,path='/'.join(autocreate_args))
        if not dest_dir.exists:
            self.makedirs(dest_dir.path)

    def copyNodeContent(self, sourceNode=None, destNode=None):
        """Copies the content of a node to another node, its used only
        if copying between different service types"""
        with sourceNode.open(mode='rb') as sourceFile:
            destNode.service.autocreate(destNode.path, autocreate=-1)
            with destNode.open(mode='wb') as destFile:
                destFile.write(sourceFile.read())

    def copy(self, source=None, dest=None):
        """Copies the content of a node to another node, 
        will use the best option available (native vs content-copy)"""
        sourceNode = self._getNode(source)
        destNode = self._getNode(dest)
        if sourceNode.isfile:
            if destNode.isdir:
                destNode = destNode.child(sourceNode.basename)
            return self._copy_file(sourceNode, destNode)
        elif sourceNode.isdir:
            return self._copy_dir(sourceNode, destNode)

    def _copy_file(self, sourceNode, destNode):
        if destNode.service.location_identifier == sourceNode.service.location_identifier:
            sourceNode.service.duplicateNode(sourceNode=sourceNode,
                destNode = destNode)
        else:
            self.copyNodeContent(sourceNode=sourceNode, destNode=destNode)
        return destNode

    def _copy_dir(self, sourceNode, destNode):
        for child in sourceNode.children():
            dest_child = destNode.child(child.basename)
            copy = self._copy_file if child.isfile else self._copy_dir
            copy(child, dest_child)
        return destNode


    def move(self, source=None, dest=None):
        """Moves the content of a node to another node, 
        will use the best option available (native vs content-copy)"""
        sourceNode = self._getNode(source)
        destNode = self._getNode(dest)
        if sourceNode.isfile:
            if destNode.isdir:
                destNode = destNode.child(sourceNode.basename)
            return self._move_file(sourceNode, destNode)
        elif sourceNode.isdir:
            return self._move_dir(sourceNode, destNode)
        

    def _move_file(self, sourceNode, destNode):
        """Moves the content of a node file to another node file, 
        will use the best option available (native vs content-copy)"""
        if destNode.service == sourceNode.service:
            sourceNode.service.renameNode(sourceNode=sourceNode,
                destNode=destNode)
        else:
            self.copyNodeContent(sourceNode=sourceNode, destNode=destNode)
            sourceNode.delete()
        return destNode
    
    def _move_dir(self, sourceNode, destNode):
        for child in sourceNode.children():
            dest_child = destNode.child(child.basename)
            move = self._move_file if child.isfile else self._move_dir
            move(child, dest_child)
        return destNode


    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        fullpath = self.internal_path(path)
        if not fullpath:
            return self.parent.not_found_exception(environ, start_response)
        existing_doc = self.exists(fullpath)
        if not existing_doc:
            return self.parent.not_found_exception(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            if_none_match = if_none_match.replace('"','')
            stats = self.stat(fullpath)
            mytime = stats.st_mtime
            size = stats.st_size
            my_none_match = "%s-%s"%(str(mytime),str(size))
            if my_none_match == if_none_match:
                headers = []
                ETAG.update(headers, my_none_match)
                start_response('304 Not Modified', headers)
                return [''] # empty body
        file_args = dict()
        if download or download_name:
            download_name = download_name or os.path.basename(fullpath)
            file_args['content_disposition'] = "attachment; filename=%s" % download_name
        with self.local_path(fullpath) as local_path:
            file_responder = fileapp.FileApp(local_path, **file_args)
            if self.parent.cache_max_age:
                file_responder.cache_control(max_age=self.parent.cache_max_age)
            return file_responder(environ, start_response)


    def _call(self, call_args=None, call_kwargs=None, cb=None, cb_args=None, cb_kwargs=None, return_output=False):
        args_list = []
        with ExitStack() as stack:
            for arg in call_args:
                if isinstance(arg, StorageNode):
                    arg = stack.enter_context(arg.local_path())
                args_list.append(arg)
            call_fn = check_output if return_output else check_call
            result = call_fn(args_list, **call_kwargs)
            if cb:
                cb(*cb_args, **cb_kwargs)
            return result

    def call(self, args, **kwargs):
        """A context manager that calls an external process on a list of files
        will work on local copies if the node is on cloud.
        if run_async==True will immediately return and the process will be managed
        by another thread,
        an optional callback (cb) can be passed to the thread an will be called 
        when the process will end, cb_args and cb_kwargs will be passed to cb"""
        cb = kwargs.pop('cb', None)
        cb_args = kwargs.pop('cb_args', None)
        cb_kwargs = kwargs.pop('cb_kwargs', None)
        run_async = kwargs.pop('run_async', None)
        return_output = kwargs.pop('return_output', None)
        call_params = dict(call_args=args,call_kwargs=kwargs, cb=cb, cb_args=cb_args, cb_kwargs=cb_kwargs, return_output=return_output)
        if run_async:
            import _thread
            _thread.start_new_thread(self._call,(),call_params)
        else:
            return self._call(**call_params)

    def listdir(self, *args, **kwargs):
        """Returns a list of paths contained in a path"""
        return [sn.fullpath for sn in self.children(*args, **kwargs)]

    def children(self, *args, **kwargs):
        """Return a list of storageNodes contained in a path"""
        pass

class BaseLocalService(StorageService):
    def __init__(self, parent=None, base_path=None, tags=None,**kwargs):
        self.parent = parent
        self.base_path =  expandpath(base_path) if base_path else None
        self.tags = tags

    @property
    def location_identifier(self):
        return 'localfs'

    def internal_path(self, *args, **kwargs):
        out_list = [self.base_path]
        # for arg in args:
        #     if '/' in arg:
        #         out_list.extend(arg.split('/'))
        #     else:
        #         out_list.append(arg)
        out_list.extend(args)
        outpath = os.path.join(*out_list)
        return outpath

    def delete_dir(self, *args):
        shutil.rmtree(self.internal_path(*args))

    def delete_file(self, *args):
        return os.unlink(self.internal_path(*args))

    def open(self, *args, **kwargs):
        return open(self.internal_path(*args), **kwargs)

    def exists(self, *args):
        return os.path.exists(self.internal_path(*args))

    def ext_attributes(self, *args):
        f_stat = self._stat(*args)
        return f_stat.st_mtime,f_stat.st_size,stat.S_ISDIR(f_stat.st_mode)


    def mtime(self, *args):
        f_stat = self._stat(*args)
        return f_stat.st_mtime

    def size(self, *args):
        f_stat = self._stat(*args)
        return f_stat.st_size

    def local_path(self, *args, **kwargs): #TODO: vedere se fare così o con altro metodo
        internalpath = self.internal_path(*args)
        return LocalPath(fullpath=internalpath)

    def makedirs(self, *args, **kwargs):
        os.makedirs(self.internal_path(*args))

    def mkdir(self, *args, **kwargs):
        if not self.exists(*args):
            os.mkdir(self.internal_path(*args))

    def _stat(self, *args):
        try:
            fileattr = os.stat(self.internal_path(*args))
        except FileNotFoundError:
            fileattr = None
        return fileattr

    def isdir(self, *args):
        if self.base_path is None:
            return False
        return os.path.isdir(self.internal_path(*args))

    def isfile(self, *args):
        return os.path.isfile(self.internal_path(*args))
    
    def md5hash(self,*args):
        import hashlib
        BLOCKSIZE = 65536
        hasher = hashlib.md5()
        with self.open(*args, mode='rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(BLOCKSIZE)
        return hasher.hexdigest()

    def renameNode(self, sourceNode=None, destNode=None):
        destNode.service.autocreate(destNode.path, autocreate=-1)
        shutil.move(sourceNode.internal_path, destNode.internal_path)

    def duplicateNode(self, sourceNode=None, destNode=None):
        destNode.service.autocreate(destNode.path, autocreate=-1)
        shutil.copy2(sourceNode.internal_path, destNode.internal_path)

    def url(self, *args, **kwargs):
        return self.internal_url(*args, **kwargs)


    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        fullpath = self.internal_path(path)
        if not fullpath:
            return self.parent.not_found_exception(environ, start_response)
        existing_doc = os.path.exists(fullpath)
        if not existing_doc:
            return self.parent.not_found_exception(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            if_none_match = if_none_match.replace('"','')
            stats = os.stat(fullpath)
            mytime = stats.st_mtime
            size = stats.st_size
            my_none_match = "%s-%s"%(str(mytime),str(size))
            if my_none_match == if_none_match:
                headers = []
                ETAG.update(headers, my_none_match)
                start_response('304 Not Modified', headers)
                return [b''] # empty body
        file_args = dict()
        if download or download_name:
            download_name = download_name or os.path.basename(fullpath)
            file_args['content_disposition'] = "attachment; filename=%s" % download_name
        file_responder = fileapp.FileApp(fullpath, **file_args)
        if self.parent.cache_max_age:
            file_responder.cache_control(max_age=self.parent.cache_max_age)
        return file_responder(environ, start_response)

    def children(self, *args, **kwargs):
        directory = sorted(os.listdir(self.internal_path(*args)))
        out = []
        for d in directory:
            subpath = os.path.join(os.path.join(*args),d)
            out.append(LegacyStorageNode(parent=self.parent, path=subpath, service=self))
        return out

class StorageResolver(BagResolver):
    """TODO"""


    classKwargs = {'cacheTime': 500,
                   'readOnly': True,
                   'invisible': False,
                   'relocate': '',
                   'ext': None,
                   'include': '',
                   'exclude': '',
                   'callback': None,
                   'dropext': False,
                   'processors': None,
                   '_page':None
    }
    classArgs = ['storageNode','relocate']

    def resolverSerialize(self):
        attr = super(StorageResolver, self).resolverSerialize()
        attr['kwargs'].pop('_page',None)
        return attr

    @property
    def service(self):
        return self.storageNode.service

    def load(self):
        """TODO"""
        extensions = dict([((ext.split(':') + (ext.split(':'))))[0:2] for ext in self.ext.split(',')]) if self.ext else dict()
        extensions['directory'] = 'directory'
        result = Bag()
        self.storageNode = self._page.site.storageNode(self.storageNode)
        try:
            directory = self.storageNode.children() or []
            directory.sort(key=lambda s:s.basename)
        except OSError:
            directory = []
        if not self.invisible:
            directory = [x for x in directory if not x.basename.startswith('.')]
        for storagenode in directory:
            fname = storagenode.basename
            nodecaption = fname
            fullpath = storagenode.fullpath
            addIt = True
            try:
                mtime,size,isdir = storagenode.ext_attributes
            except TypeError:
                mtime,size,isdir = None,None,None
            if isdir:
                ext = 'directory'
                if self.exclude:
                    addIt = gnrstring.filter(fname, exclude=self.exclude, wildcard='*')
            else:
                if self.include or self.exclude:
                    addIt = gnrstring.filter(fname, include=self.include, exclude=self.exclude, wildcard='*')
                fname, ext = os.path.splitext(fname)
                ext = ext[1:]
            if addIt:
                label = self.makeLabel(fname, ext)
                processors = self.processors or {}
                processname = extensions.get(ext.lower(), None)
                handler = processors.get(processname)
                if handler is not False:
                    handler = handler or getattr(self, 'processor_%s' % extensions.get(ext.lower(), 'None'), None)
                handler = handler or self.processor_default
                caption = fname.replace('_',' ').strip()
                m=re.match(r'(\d+) (.*)',caption)
                caption = '!!%s %s' % (str(int(m.group(1))),m.group(2).capitalize()) if m else caption.capitalize()
                nodeattr = dict(file_name=fname, file_ext=ext, storage=storagenode.service.service_name,
                               abs_path=fullpath,url=storagenode.url(), mtime=mtime, nodecaption=nodecaption,
                               caption=caption,size=size,
                               internal_url=storagenode.internal_url())
                if self.callback:
                    cbres = self.callback(nodeattr=nodeattr)
                    if cbres is False:
                        continue
                result.setItem(label, handler(storagenode) ,**nodeattr)
        return result

    def makeLabel(self, name, ext):
        """TODO

        :param name: TODO
        :param ext: TODO"""
        if ext != 'directory' and not self.dropext:
            name = '%s_%s' % (name, ext)
        return name.replace('.', '_')

    def processor_directory(self, storagenode):
        """TODO

        :param path: TODO"""
        return StorageResolver(storagenode.fullpath, **self.instanceKwargs)

    def processor_xml(self, storagenode):
        """TODO

        :param path: TODO"""
        kwargs = dict(self.instanceKwargs)
        kwargs['storagenode'] = storagenode
        return XmlStorageResolver(**kwargs)

    processor_xsd = processor_xml

    processor_html = processor_xml


    def processor_txt(self, storagenode):
        """TODO

        :param path: TODO"""
        kwargs = dict(self.instanceKwargs)
        kwargs['storagenode'] = storagenode
        return TxtStorageResolver(**kwargs)

    def processor_default(self, path):
        """TODO

        :param path: TODO"""
        return None

    def get_metadata(self, path):
        pass

    def set_metadata(self, path, metadata):
        pass


class TxtStorageResolver(BagResolver):
    classKwargs = {'cacheTime': 500,
                   'readOnly': True
    }
    classArgs = ['storagenode']

    def load(self):
        with self.storagenode.open() as f:
            return f.read()

class XmlStorageResolver(BagResolver):
    classKwargs = {'cacheTime': 500,
                   'readOnly': True
    }
    classArgs = ['storagenode']

    def load(self):
        with self.storagenode.open() as xmlfile:
            b = Bag()
            b.fromXml(xmlfile.read())
            return b


# ==================== Storage Handlers ====================

class BaseStorageHandler(object):
    """Base class for storage handlers.

    A storage handler manages the creation of storage nodes and determines
    which implementation (Legacy or New) to use.
    """

    def __init__(self, site):
        """Initialize the storage handler.

        Args:
            site: The GnrWsgiSite instance
        """
        self.site = site

    def getVolumeService(self, storage_name=None):
        sitevolumes = self.site.config.getItem('volumes')
        if sitevolumes and storage_name in sitevolumes:
            vpath = sitevolumes.getAttr(storage_name,'path')
        else:
            vpath = storage_name
        volume_path = expandpath(os.path.join(self.site.site_static_dir,vpath))
        return self.site.getService(service_type='storage',service_name=storage_name
            ,implementation='local',base_path=volume_path)

    def storagePath(self, storage_name, storage_path):
        if storage_name == 'user':
            return '%s/%s'%(self.site.currentPage.user, storage_path)
        elif storage_name == 'conn':
            return '%s/%s'%(self.site.currentPage.connection_id, storage_path)
        elif storage_name == 'page':
            return '%s/%s/%s'% (self.site.currentPage.connection_id, self.site.currentPage.page_id, storage_path)
        return storage_path

    def storage(self, storage_name,**kwargs):
        storage = self.site.getService(service_type='storage',service_name=storage_name)
        if not storage:
            storage = self.getVolumeService(storage_name=storage_name)
        return storage

    def storageNode(self, *args, **kwargs):
        """Create a storage node.

        Args:
            *args: Path components
            **kwargs: Storage node options

        Returns:
            BaseStorageNode: A storage node instance
        """
        raise NotImplementedError("Subclasses must implement storageNode()")

    @property
    def storageTypes(self):
        return ['_storage','_site','_dojo','_gnr','_conn',
                '_pages','_rsrc','_pkg','_pages',
                '_user','_vol', '_documentation']

    def storageType(self, path_list=None):
        first_segment = path_list[0]
        if ':' in first_segment:
            return first_segment
        else:
            for k in self.storageTypes:
                if first_segment.startswith(k):
                    return k[1:]

    def storageNodeFromPathList(self, path_list=None, storageType=None):
        "Returns storageNode from path_list"
        if not storageType:
            storageType = self.storageType(path_list)
        if ':' in storageType:
            #site:image -> site
            storage_name, path_list[0] = storageType.split(':')
        elif storageType == 'storage':
            #/_storage/site/pippo -> site
            storage_name, path_list = path_list[1], path_list[2:]
        else:
            #_vol/pippo -> vol
            storage_name = storageType
            path_list.pop(0)

        path = '/'.join(path_list)
        return self.storageNode('%s:%s'%(storage_name,path),_adapt=False)

    def storageDispatcher(self,path_list,environ,start_response,storageType=None,**kwargs):
        storageNode = self.storageNodeFromPathList(path_list, storageType)
        exists = storageNode and storageNode.exists
        if not exists and '_lazydoc' in kwargs:
            #fullpath = None ### QUI NON DOBBIAMO USARE I FULLPATH
            exists = self.site.build_lazydoc(kwargs['_lazydoc'],fullpath=storageNode.internal_path,**kwargs)
            exists = exists and storageNode.exists

        # WHY THIS?
        self.site.db.closeConnection()
        if not exists:
            if kwargs.get('_lazydoc'):
                headers = []
                start_response('200 OK', headers)
                return ['']
            return self.site.not_found_exception(environ, start_response)
        return storageNode.serve(environ, start_response,**kwargs)

    def getStaticPath(self, static, *args, **kwargs):
        """TODO

        :param static: TODO"""
        static_name, static_path = static.split(':',1)

        symbolic = kwargs.pop('symbolic', False)
        if symbolic:
            return self.storageNode(static, *args).fullpath
        autocreate = kwargs.pop('autocreate', False)
        if not ':' in static:
            return static

        args = self.adaptStaticArgs(static_name, static_path, args)
        static_handler = self.site.getStatic(static_name)
        if autocreate and static_handler.supports_autocreate:
            assert autocreate == True or autocreate < 0
            if autocreate != True:
                autocreate_args = args[:autocreate]
            else:
                autocreate_args = args
            dest_dir = static_handler.path(*autocreate_args)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
        dest_path = static_handler.path(*args)
        return dest_path


    def getStaticUrl(self, static, *args, **kwargs):
        """TODO

        :param static: TODO"""
        if not ':' in static:
            return static
        static_name, static_url = static.split(':',1)
        args = self.adaptStaticArgs(static_name, static_url, args)
        return self.storage(static_name).url(*args, **kwargs)

    def adaptStaticArgs(self, static_name, static_path, args):
        """TODO

        :param static_name: TODO
        :param static_path: TODO
        :param args: TODO"""
        args = tuple(static_path.split(os.path.sep)) + args
        if static_name == 'user':
            args = (self.site.currentPage.user,) + args #comma does matter
        elif static_name == 'conn':
            args = (self.site.currentPage.connection_id,) + args
        elif static_name == 'page':
            args = (self.site.currentPage.connection_id, self.site.currentPage.page_id) + args
        return args


class LegacyStorageHandler(BaseStorageHandler):
    """Legacy storage handler that creates LegacyStorageNode instances."""

    def storageNode(self, *args, **kwargs):
        """Create a legacy storage node.

        This method contains the original storageNode logic from GnrWsgiSite.

        Args:
            *args: Path components (mount:path or separate args)
            **kwargs: Options including:
                - _adapt: Whether to adapt path (default True)
                - autocreate: Auto-create directories
                - must_exist: Raise error if doesn't exist
                - version: Version specifier
                - mode: Access mode

        Returns:
            LegacyStorageNode: A legacy storage node instance
        """
        # Handle StorageNode passthrough
        if args and isinstance(args[0], BaseStorageNode):
            if args[1:]:
                return self.storageNode(args[0].fullpath, *args[1:])
            else:
                return args[0]

        # Build path from args
        path = '/'.join(args) if args else None
        if not path:
            return None

        # Add default mount if no ':' in path
        if ':' not in path:
            path = '_raw_:%s' % path

        # Handle HTTP URLs
        if path.startswith('http://') or path.startswith('https://'):
            path = '_http_:%s' % path

        # Parse mount:path
        service_name, storage_path = path.split(':', 1)
        storage_path = storage_path.lstrip('/')

        # Handle legacy 'vol:' format
        if service_name == 'vol':
            # vol:name/path -> name:path
            service_name, storage_path = storage_path.replace(':', '/').split('/', 1)

        # Get storage service
        service = self.storage(service_name)

        # Adapt path for special mounts (user, conn, page)
        if kwargs.pop('_adapt', True):
            storage_path = self.storagePath(service_name, storage_path)

        if not service:
            return None

        # Extract parameters
        autocreate = kwargs.pop('autocreate', False)
        must_exist = kwargs.pop('must_exist', False)
        version = kwargs.pop('version', None)
        mode = kwargs.pop('mode', None)

        return LegacyStorageNode(
            parent=self.site,
            path=storage_path,
            service=service,
            autocreate=autocreate,
            must_exist=must_exist,
            mode=mode,
            version=version
        )
