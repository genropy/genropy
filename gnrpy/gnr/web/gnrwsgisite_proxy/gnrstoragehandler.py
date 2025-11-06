#!/usr/bin/env python
# encoding: utf-8
import os

from gnr.lib.services.storage import StorageNode as LegacyStorageNode
from gnr.core.gnrsys import expandpath
#from genro_storage import StorageNode as BrickStorageNode

#class NewStorageNode(object):
#    def __init__(self,*args,**kwargs):
#        self._node = BrickStorageNode


class BaseStorageHandler:
    """Base class for storage handling."""

    def __init__(self, site):
        self.site = site

    def getVolumeService(self, storage_name=None):
        sitevolumes = self.site.config.getItem('volumes')
        if sitevolumes and storage_name in sitevolumes:
            vpath = sitevolumes.getAttr(storage_name, 'path')
        else:
            vpath = storage_name
        volume_path = expandpath(os.path.join(self.site.site_static_dir, vpath))
        return self.site.getService(service_type='storage', service_name=storage_name,
                                    implementation='local', base_path=volume_path)

    def storagePath(self, storage_name, storage_path):
        if storage_name == 'user':
            return '%s/%s' % (self.site.currentPage.user, storage_path)
        elif storage_name == 'conn':
            return '%s/%s' % (self.site.currentPage.connection_id, storage_path)
        elif storage_name == 'page':
            return '%s/%s/%s' % (self.site.currentPage.connection_id,
                               self.site.currentPage.page_id, storage_path)
        return storage_path

    def storageService(self, storage_name, **kwargs):
        storage = self.site.getService(service_type='storage', service_name=storage_name)
        if not storage:
            storage = self.getVolumeService(storage_name=storage_name)
        return storage

    def storageNode(self, *args, **kwargs):
        if not isinstance(args[0], str):
            if args[1:]:
                return self.storageNode(args[0].fullpath, *args[1:], **kwargs)
            else:
                return args[0]
        return self.makeNode(*args,**kwargs)
        
class LegacyStorageHandler(BaseStorageHandler):
    """Legacy storage handler implementation."""

    def _adapt_path(self,*args,**kwargs):
        path = '/'.join(args)
        if not ':' in path:
            path = '_raw_:%s' % path
        if path.startswith('http://') or path.startswith('https://'):
            path = '_http_:%s' % path
        service_name, storage_path = path.split(':', 1)
        storage_path = storage_path.lstrip('/')
        if service_name == 'vol':
            #for legacy path
            service_name, storage_path = storage_path.replace(':', '/').split('/', 1)
        return service_name,storage_path

    def makeNode(self,*args,**kwargs):
        service_name,storage_path = self._adapt_path(*args,**kwargs)
        service = self.storageService(service_name)
        if kwargs.pop('_adapt', True):
            storage_path = self.storagePath(service_name, storage_path)
        if not service:
            return None
        return LegacyStorageNode(parent=self.site,service=service, path=storage_path, **kwargs)

