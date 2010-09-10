# -*- coding: UTF-8 -*-
from gnr.core.gnrbag import Bag
import inspect
import os
import sys
from gnr.core.gnrsys import expandpath
from paste import fileapp
from paste.httpheaders import ETAG


class StaticHandlerManager(object):
    """ This class handles the StaticHandlers"""
    
    def __init__(self, site):
        self.site=site
        self.statics=Bag()
        
    def addAllStatics(self,module=None):
        module = module or sys.modules[self.__module__]
        """inspect self (or other modules) for StaticHandler subclasses and 
        do addStatic for each"""
        def is_StaticHandler(cls):
            return inspect.isclass(cls) and issubclass(cls,StaticHandler) and cls is not StaticHandler
        statichandler_classes = inspect.getmembers(module, is_StaticHandler)
        for statichandler in statichandler_classes:
            self.add(statichandler[1])
        
    def add(self, static_handler_factory, **kwargs):
        static_handler=static_handler_factory(self.site,**kwargs)
        self.statics.setItem(static_handler.prefix,static_handler,**kwargs)
        
    def get(self,static_name):
        return self.statics[static_name]
        
    def static_dispatcher(self,path_list,environ,start_response,download=False,**kwargs):
        handler = self.get(path_list[0][1:])
        if handler:
            return handler.serve(path_list,environ,start_response,download=False,**kwargs)
        else:
            return self.site.not_found_exception(environ, start_response)



class StaticHandler(object):
    """ implementor=self.site.get_implementor('dojo')
    "/_dojo/11/dojo/dojo/dojo.js"=implementor.relative_url(*args)
    "http://www.pippone.com/mysite/_dojo/11/dojo/dojo/dojo.js"=implementor.external_url(*args)
    "http://localhost:8088/_dojo/11/dojo/dojo/dojo.js"=implementor.local_url(*args)
    result=implementor.serve(*args)
    '/Users/genro/develop/dojo11/dojo/dojo.js'=implementor.path(*args)
    implementor()
    def dojo_static_path(self, version,*args):
        return expandpath(os.path.join(self.dojo_path[version], *args))

    def dojo_static_url(self, version,*args):
        return '%s_dojo/%s/%s'%(self.home_uri,version,'/'.join(args))"""  
    def __init__(self, site, **kwargs):
        self.site=site
        
    @property
    def home_uri(self):
        return self.site.home_uri
    
    def absolute_url(self,external=True, *args):
        pass

    def serve(self,path_list,environ,start_response,download=False,**kwargs):
        fullpath = self.path(*path_list[1:])
        if fullpath and not os.path.isabs(fullpath):
            fullpath = os.path.normpath(os.path.join(self.site_path,fullpath))
        if fullpath and not os.path.exists(fullpath):
            return self.site.not_found_exception(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            mytime = os.stat(fullpath).st_mtime
            if str(mytime) == if_none_match:
                headers = []
                ETAG.update(headers, mytime)
                start_response('304 Not Modified', headers)
                return [''] # empty body
        file_args=dict()
        if download:
            file_args['content_disposition']="attachment; filename=%s" % os.path.basename(fullpath)
        file_responder = fileapp.FileApp(fullpath,**file_args)
        if self.site.cache_max_age:
            file_responder.cache_control(max_age=self.site.cache_max_age)
        return file_responder(environ, start_response)

    
class DojoStaticHandler(StaticHandler):
    prefix='dojo'
    def url(self, version ,*args):
        return '%s_dojo/%s/%s'%(self.home_uri,version,'/'.join(args))
    
    def path(self, version ,*args):
        return expandpath(os.path.join(self.site.dojo_path[version], *args))
        
class SiteStaticHandler(StaticHandler):
    prefix='site'
    def url(self ,*args):
        return '%s_site/%s'%(self.home_uri,'/'.join(args))
    
    def path(self ,*args):
        return expandpath(os.path.join(self.site.site_static_dir, *args))

class PkgStaticHandler(StaticHandler):
    prefix='pkg'
    def path(self,pkg,*args):
        return os.path.join(self.site.gnrapp.packages[pkg].packageFolder,'webpages', *args)

    def url(self,pkg,*args):
        return '%s_pkg/%s/%s'%(self.home_uri,pkg,'/'.join(args))
    
class RsrcStaticHandler(StaticHandler):
    prefix='rsrc'
    def path(self,resource_id,*args):
        resource_path = self.site.resources.get(resource_id)
        if resource_path:
            return os.path.join(resource_path, *args)
    
    def url(self,resource_id,*args):
        return '%s_rsrc/%s/%s'%(self.home_uri,resource_id,'/'.join(args))


class PagesStaticHandler(StaticHandler):
    prefix='pages'
    def path(self,*args):
        return os.path.join(self.site_path,'pages', *args)
    
    def url(self,*args):
        return '%s_pages/%s'%(self.home_uri,'/'.join(args))

class GnrStaticHandler(StaticHandler):
    prefix='gnr'
    def path(self, version,*args):
        return expandpath(os.path.join(self.site.gnr_path[version], *args))

    def url(self, version,*args):
        return '%s_gnr/%s/%s'%(self.home_uri,version,'/'.join(args))
        
class ConnectionStaticHandler(StaticHandler):
    prefix='conn'
    def path(self,connection_id,page_id,*args):
        return os.path.join(self.site.site_path,'data','_connections', connection_id, page_id, *args)
        
    def url(self, page,*args):
        return '%s_conn/%s/%s/%s'%(self.home_uri,page.connection_id, page.page_id,'/'.join(args))


class UserStaticHandler(StaticHandler):
    prefix='user'
    def path(self,user,page_id,*args):
        return os.path.join(self.site.site_path,'data','_users', user, page_id, *args)
        
    def url(self, page,*args):
        return '%s_user/%s/%s/%s'%(self.home_uri,page.user or 'Anonymous', page.page_id,'/'.join(args))