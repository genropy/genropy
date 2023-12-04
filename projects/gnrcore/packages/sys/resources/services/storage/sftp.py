# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 Softwell. All rights reserved.

from builtins import object
from gnr.lib.services.storage import StorageService,StorageNode,StorageResolver
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from collections import defaultdict
import _thread
from threading import RLock
#from gnr.core.gnrlang import componentFactory
try: 
    import paramiko
except ImportError:
    paramiko = False
import stat
import os
import tempfile
import mimetypes
from datetime import datetime
from paste import fileapp
from paste.httpheaders import ETAG
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<ssl.SSLSocket.*>")


class SFTPTemporaryFilename(object):
    def __init__(self,parent=None, mode=None, remote_path=None,
                keep=False, ):
        self.parent = parent
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
            self.parent.sftp.get(self.remote_path, self.name)
            self.enter_mtime = os.stat(self.name).st_mtime
        except FileNotFoundError:
            self.enter_mtime = None
        return self.name

    def __exit__(self, exc, value, tb):
        if os.stat(self.name).st_mtime != self.enter_mtime:
            self.sftp.put(self.name, self.remote_path)
        if not self.keep:
            os.unlink(self.name)

class Service(StorageService):

    def __init__(self, parent=None, host=None, port=22,
        base_path=None, username=None,
        password=None,  **kwargs):
        self.parent = parent
        self.host = host
        self.port = int(port)
        self.base_path = (base_path or '').rstrip('/')
        self.username = username
        self.password = password
        self._thclient = dict()
        self.lock = RLock()
        #self.transport = paramiko.Transport((self.host, self.port))

    def _new_client(self):
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username = self.username, password = self.password)
        client = paramiko.SFTPClient.from_transport(transport)
        client.sock.settimeout(1.5)
        return client

    def _client_alive(self, client):
        if not client:
            return False
        try:
            client.stat('')
            return True
        except (TimeoutError,paramiko.SSHException):
            return False

    @property
    def sftp(self):
        if not paramiko:
            raise GnrException('Missing required library paramiko. Please run pip install paramiko')
        thread_ident = _thread.get_ident()
        client = self._thclient.get(thread_ident)
        if not self._client_alive(client):
            self.lock.acquire()
            client = self._thclient[thread_ident] = self._new_client()
            self.lock.release()
        return client


    @property
    def location_identifier(self):
        return 'sftp/%s/%s' % (self.host.replace('.','_'), self.username)

    def internal_path(self, *args):
        out_list = [self.base_path]
        out_list.extend(args)
        outpath = '/'.join(out_list)
        return outpath.strip('/').replace('//','/')

    def _stat(self, *args):
        try:
            fileattr = self.sftp.stat(self.internal_path(*args))
        except FileNotFoundError:
            fileattr = None
        return fileattr

    def isfile(self, *args):
        f_stat = self._stat(*args)
        return stat.S_ISREG(f_stat.st_mode) if f_stat else False


    def md5hash(self,*args):
        import hashlib
        BLOCKSIZE = 65536
        hasher = hashlib.new('md5', usedforsecurity=False)
        with self.open(*args, mode='rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(BLOCKSIZE)
        return hasher.hexdigest()

    def exists(self, *args):
        return self._stat(*args) is not None

    def makedirs(self, *args, **kwargs):
        pass

    def mkdir(self, *args, **kwargs):
        self.sftp.mkdir(self.internal_path(*args))

    def ext_attributes(self, *args):
        f_stat = self._stat(*args)
        if f_stat:
            return f_stat.st_mtime,f_stat.st_size,stat.S_ISDIR(f_stat.st_mode)
        else:
            return None,None,None

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
        self.sftp.remove(self.internal_path(*args))

    def delete_dir(self, *args):
        self.sftp.rmdir(self.internal_path(*args))

    def url(self, *args, **kwargs):
        return self.internal_url(*args, **kwargs)

    def internal_url(self, *args, **kwargs):
        kwargs = kwargs or {}
        kwargs['_download'] = True
        return super(Service, self).internal_url(*args, **kwargs)

    def open(self, *args, **kwargs):
        kwargs['mode'] = kwargs.get('mode', 'rb')
        return self.sftp.open(self.internal_path(*args), **kwargs)

    def duplicateNode(self, sourceNode=None, destNode=None): # will work only in the same bucket
        destNode.service.autocreate(destNode.path, autocreate=-1)
        self.copyNodeContent(sourceNode=sourceNode, destNode=destNode)
        sourceNode.delete()

    def renameNode(self, sourceNode=None, destNode=None):
        destNode.service.autocreate(destNode.path, autocreate=-1)
        self.sftp.posix_rename(sourceNode.internal_path, destNode.internal_path)
        return destNode

    def children(self, *args, **kwargs):
        directory = sorted(self.sftp.listdir(self.internal_path(*args)))
        out = []
        for d in directory:
            subpath = os.path.join(os.path.join(*args),d)
            out.append(StorageNode(parent=self.parent, path=subpath, service=self))
        return out

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
