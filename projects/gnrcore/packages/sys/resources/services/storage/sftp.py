
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 Softwell. All rights reserved.

from builtins import object
from gnr.lib.services.storage import StorageService,StorageNode,StorageResolver
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
#from gnr.core.gnrlang import componentFactory
import paramiko
import stat
import os
import tempfile
import mimetypes
from datetime import datetime
from paste import fileapp
from paste.httpheaders import ETAG
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<ssl.SSLSocket.*>")


class SFTPConnection(object):
    def __init__(self, parent=None, host=None, port=22,
        username=None,
        password=None, transport=None):
        if parent:
            self.host = parent.host
            self.port = parent.port
            self.username = parent.username
            self.password = parent.password
            self.transport = parent.transport
        else:
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.transport = transport
        self.keep_transport_open = self.transport is not None and transport.is_active()
        self.transport = self.transport or paramiko.Transport((self.host, self.port))

    def __enter__(self):
        self.fd,self.name = tempfile.mkstemp(suffix=self.ext)
        if not self.transport.is_active():
            self.transport.connect(username = self.username, password = self.password)
        return paramiko.SFTPClient.from_transport(self.transport)
    def __exit__(self, exc, value, tb):
        if not self.keep_transport_open:
            self.transport.close()


class SFTPTemporaryFilename(object):
    def __init__(self,parent=None, host=None, port=22, mode=None, remote_path=None, username=None, password=None,
                keep=False, transport=None):
        if parent:
            self.host = parent.host
            self.port = parent.port
            self.username = parent.username
            self.password = parent.password
            self.transport = parent.transport
        else:
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.transport = transport
        self.keep_transport_open = self.transport is not None and transport.is_active()
        self.transport = self.transport or paramiko.Transport((self.host, self.port))
        self.mode = mode or 'r'
        self.write_mode = ('w' in self.mode) or False
        self.read_mode = not self.write_mode
        self.remote_path = remote_path
        self.file = None
        self.ext = os.path.splitext(self.remote_path)[-1]
        self.keep = keep

    def __enter__(self):
        self.fd,self.name = tempfile.mkstemp(suffix=self.ext)
        try:
            with SFTPConnection(self) as sftp:
                sftp.get(self.remote_path, self.name)
            self.enter_mtime = os.stat(self.name).st_mtime
        except:
            self.enter_mtime = None
        return self.name

    def __exit__(self, exc, value, tb):
        if os.stat(self.name).st_mtime != self.enter_mtime:
            with SFTPConnection(self) as sftp:
                sftp.put(self.name, self.remote_path)
        if not self.keep:
            os.unlink(self.name)


class Service(StorageService):

    def __init__(self, parent=None, host=None, port=22,
        base_path=None, username=None,
        password=None,  **kwargs):
        self.parent = parent
        self.host = host
        self.port = port
        self.base_path = (base_path or '').rstrip('/')
        self.username = username
        self.password = password
        self.transport = paramiko.Transport((self.host, self.port))

    @property
    def location_identifier(self):
        return 'sftp/%s/%s' % (self.host.replace('.','_'), self.username)

    def internal_path(self, *args):
        out_list = [self.base_path]
        out_list.extend(args)
        outpath = '/'.join(out_list)
        return outpath.strip('/').replace('//','/')

    @property
    def sftp(self):
        return SFTPConnection(self)

    def _stat(self, *args):
        internalpath = self.internal_path(*args)
        if internalpath =='':
            return False
        with SFTPConnection(self) as sftp:
            try:
                fileattr = sftp.stat(internalpath)
            except FileNotFoundError:
                return None

    def isfile(self, *args):
        f_stat = self._stat(*args)
        return stat.S_ISREG(f_stat.st_mode) if f_stat else False


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

    def exists(self, *args):
        return self._stat(*args) is None

    def makedirs(self, *args, **kwargs):
        pass

    def mkdir(self, *args, **kwargs):
        internalpath = self.internal_path(*args)
        with SFTPConnection(self) as sftp:
            sftp.mkdir(internalpath)

    def mtime(self, *args):
        f_stat = self._stat(*args)
        return f_stat.st_mtime if f_stat else None

    def size(self, *args):
        f_stat = self._stat(*args)
        return f_stat.st_size if f_stat else None

    def local_path(self, *args, **kwargs):
        mode = kwargs.get('mode', 'r')
        keep = kwargs.get('keep', False)
        internalpath = self.internal_path(*args)
        return SFTPTemporaryFilename(self, remote_path=internalpath,
            mode=mode, keep=keep)

    def isdir(self, *args):
        f_stat = self._stat(*args)
        return stat.S_ISDIR(f_stat.st_mode) if f_stat else False


    def delete_file(self, *args):
        internalpath = self.internal_path(*args)
        with SFTPConnection(self) as sftp:
            sftp.remove(internalpath)
    def delete_dir(self, *args):
        internalpath = self.internal_path(*args)
        with SFTPConnection(self) as sftp:
            sftp.rmdir(internalpath)

    def url(self, *args, **kwargs):
        return self.internal_url(*args, **kwargs)
    def internal_url(self, *args, **kwargs):
        kwargs = kwargs or {}
        kwargs['_download'] = True
        return super(Service, self).internal_url(*args, **kwargs)

    def open(self, *args, **kwargs):
        kwargs['mode'] = kwargs.get('mode', 'rb')
        with SFTPConnection(self) as sftp:
            return sftp.open(self.internal_path(*args), **kwargs)

    def duplicateNode(self, sourceNode=None, destNode=None): # will work only in the same bucket
        destNode.service.autocreate(destNode.path, autocreate=-1)
        self.copyNodeContent(sourceNode=sourceNode, destNode=destNode)
        sourceNode.delete()

    def renameNode(self, sourceNode=None, destNode=None):
        destNode.service.autocreate(destNode.path, autocreate=-1)
        with SFTPConnection(self) as sftp:
            sftp.posix_rename(sourceNode.internal_path, destNode.internal_path)
        return destNode

    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        if download or download_name:
            download_name = download_name or self.basename(path)
            content_disposition = "attachment; filename=%s" % download_name
        else:
            content_disposition = "inline"
        url = self.url(path, _content_disposition=content_disposition)
        if url:
            return self.parent.redirect(environ, start_response, location=url,temporary=True)

    def children(self, *args, **kwargs):
        with SFTPConnection(self) as sftp:
            directory = sorted(sftp.listdir(self.internal_path(*args)))
        out = []
        for d in directory:
            subpath = os.path.join(os.path.join(*args),d)
            out.append(StorageNode(parent=self.parent, path=subpath, service=self))
        return out

    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        fullpath = self.internal_path(path)
        if not fullpath:
            return self.parent.not_found_exception(environ, start_response)
        with SFTPConnection(self) as sftp:
            existing_doc = os.path.exists(fullpath)
            if not existing_doc:
                return self.parent.not_found_exception(environ, start_response)
            if_none_match = environ.get('HTTP_IF_NONE_MATCH')
            if if_none_match:
                if_none_match = if_none_match.replace('"','')
                stats = sftp.stat(fullpath)
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
            with self.local_path() as localpath:
                file_responder = fileapp.FileApp(localpath, **file_args)
                if self.parent.cache_max_age:
                    file_responder.cache_control(max_age=self.parent.cache_max_age)
            return file_responder(environ, start_response)


class ServiceParameters(BaseComponent):
    py_requires = 'gnrcomponents/storagetree:StorageTree'
    def service_parameters(self,pane,datapath=None,**kwargs):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').formbuilder(datapath=datapath)
        fb.textbox(value='^.host',lbl='Host')
        fb.textbox(value='^.base_path',lbl='Base path')
        fb.textbox(value='^.port',lbl='Port')
        fb.textbox(value='^.username',lbl='Username')
        fb.textbox(value='^.password',lbl='Password')
        bc.storageTreeFrame(frameCode='sftpStorage',storagepath='^#FORM.record.service_name?=#v+":"',
                                border='1px solid silver',margin='2px',rounded=4,
                                region='center',preview_region='right',
                                store__onBuilt=1,
                                preview_border_left='1px solid silver',preview_width='50%')
