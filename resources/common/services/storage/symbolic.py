#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-

from gnr.lib.services.storage import BaseLocalService
from gnr.web.gnrbaseclasses import BaseComponent
import os
import tempfile
from gnr.core.gnrsys import expandpath

class Service(BaseLocalService):

    @property
    def home_uri(self):
        return self.parent.default_uri
    
    @property
    def site_path(self):
        return self.parent.storageNode('site:').internal_path

    def path_rsrc(self, resource_id, *args, **kwargs):
        resource_path = self.parent.resources.get(resource_id)
        if resource_path:
            return os.path.join(resource_path, *args)

    def path_page(self, connection_id, page_id, *args, **kwargs):
        os.path.join(self.site_path, 'data', '_connections', connection_id, page_id, *args)

    def path_pages(self,  *args, **kwargs):
        os.path.join(self.site_path, 'pages', *args)

    def path_conn(self, connection_id, *args, **kwargs):
        return os.path.join(self.site_path, 'data', '_connections', connection_id, *args)

    def path_dojo(self, version, *args, **kwargs):
        return expandpath(os.path.join(self.parent.dojo_path[version], *args))

    def path_pkg(self, pkg, *args, **kwargs):
        return os.path.join(self.parent.gnrapp.packages[pkg].packageFolder, *args)

    def path_gnr(self, version, *args, **kwargs):
        return expandpath(os.path.join(self.parent.gnr_path[version], *args))

    def path_temp(self, *args, **kwargs):
        return os.path.join(tempfile.gettempdir(), *args)

    def path_user(self, user, *args, **kwargs):
        return os.path.join(self.site_path, 'data', '_users', user, *args)

    def url_site(self, *args, **kwargs):
        return '%s_site/%s' % (self.home_uri, '/'.join(args))

    def url_rsrc(self, resource_id, *args, **kwargs):
        return '%s_rsrc/%s/%s' % (self.home_uri, resource_id, '/'.join(args))

    def url_page(self, connection_id, page_id, *args, **kwargs):
        return '%s_page/%s/%s/%s' % (self.home_uri, connection_id, page_id, '/'.join(args))

    def url_pages(self,  *args, **kwargs):
        return '%s_pages/%s' % (self.home_uri, '/'.join(args))


    def url_conn(self, connection_id, *args, **kwargs):
        return '%s_conn/%s/%s' % (self.home_uri, connection_id, '/'.join(args))

    def url_dojo(self, version, *args, **kwargs):
        if kwargs.get('_localroot'):
            return '%s_dojo/%s/%s' % (kwargs.get('_localroot'), version, '/'.join(args))
        return '%s_dojo/%s/%s' % (self.home_uri, version, '/'.join(args))

    def url_pkg(self, pkg, *args, **kwargs):
        return '%s_pkg/%s/%s' % (self.home_uri, pkg, '/'.join(args))

    def url_gnr(self, version, *args, **kwargs):
        if kwargs.get('_localroot'):
            return '%s_gnr/%s/%s' % (kwargs.get('_localroot'), version, '/'.join(args))
        else:
            return '%s_gnr/%s/%s' % (self.home_uri, version, '/'.join(args))

    def url_temp(self, path):
        pass

    def url_user(self, user, *args, **kwargs):
        return '%s_user/%s/%s' % (self.home_uri, user, '/'.join(args))


    def url_vol(self, volume, *args, **kwargs):
        return '%s_vol/%s/%s' % (self.home_uri, volume, '/'.join(args))

    def path_vol(self,volume,*args,**kwargs):
        sitevolumes = self.parent.config.getItem('volumes')
        if sitevolumes and volume in sitevolumes:
            vpath = sitevolumes.getAttr(volume,'path')
        else:
            vpath = volume
        return expandpath(os.path.join(self.parent.site_static_dir,vpath, *args))

    def internal_path(self, *args, **kwargs):
        path = self._argstopath(*args)
        path_getter = getattr(self, 'path_%s'%self.service_name, None)
        if path_getter:
            return path_getter(*(path.split('/')), **kwargs)

    def url(self, *args, **kwargs):
        path = self._argstopath(*args)
        url_getter = getattr(self, 'url_%s'%self.service_name, None)
        if url_getter:
            return url_getter(*(path.split('/')), **kwargs)

