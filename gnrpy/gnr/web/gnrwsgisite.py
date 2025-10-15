import os
import re
import io
import shutil
import subprocess
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urlsplit
import _thread
import mimetypes
import functools
from time import time
from collections import defaultdict
from threading import RLock
import warnings

import requests
from werkzeug.wrappers import Request, Response
from webob.exc import (WSGIHTTPException, HTTPInternalServerError,
                       HTTPNotFound, HTTPForbidden, HTTPPreconditionFailed,
                       HTTPClientError, HTTPMovedPermanently,HTTPTemporaryRedirect )

from gnr.core.gnrbag import Bag
from gnr.core import gnrstring
from gnr.core.gnrlang import GnrException,GnrDebugException,tracebackBag,getUuid
from gnr.core.gnrdecorator import public_method, deprecated
from gnr.core.gnrconfig import getGnrConfig,getEnvironmentItem
from gnr.core.gnrsys import expandpath
from gnr.core.gnrstring import boolean
from gnr.core.gnrdecorator import extract_kwargs,metadata
from gnr.core.gnrcrypto import AuthTokenGenerator
from gnr.lib.services import ServiceHandler
from gnr.lib.services.storage import StorageNode
from gnr.app.gnrdeploy import PathResolver
from gnr.app.gnrapp import GnrPackage
from gnr.web import logger
from gnr.web.gnrwebapp import GnrWsgiWebApp
from gnr.web.gnrwebpage import GnrUnsupportedBrowserException, GnrMaintenanceException
from gnr.web.gnrwebreqresp import GnrWebRequest
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader
from gnr.web.gnrwsgisite_proxy.gnrstatichandler import StaticHandlerManager
from gnr.web.gnrwsgisite_proxy.gnrpwahandler import PWAHandler
from gnr.web.gnrwsgisite_proxy.gnrsiteregister import SiteRegisterClient
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import WsgiWebSocketHandler

try:
    from werkzeug import EnvironBuilder
except ImportError:
    from werkzeug.test import EnvironBuilder

mimetypes.init()

IS_MOBILE = re.compile(r'iPhone|iPad|Android')

warnings.simplefilter("default")
global GNRSITE


def currentSite():
    global GNRSITE
    return GNRSITE #JBE Why does this generate an error on Saving the doc == Undefined Name 'GNRSITE' ==?

class GnrSiteException(GnrException):
    """Standard Genro Site Exception

    * **code**: GNRSITE-001
    * **description**: Genro Site Exception
    """
    code = 'GNRSITE-001'
    description = '!!Genro Site exception'
    caption = "!! Site Error : %(message)s"

class GnrWebServerError(Exception):
    pass

class PrintHandlerError(Exception):
    pass


class PathResolution(object):
    __slots__ = ('path_list', 'redirect_to', 'matched_domain', 'matched_static_route',
                 'base_dbstore', 'original_path', 'normalized_path')

    def __init__(self, path_list, redirect_to=None, matched_domain=None,
                 matched_static_route=None, base_dbstore=None, original_path=None,
                 normalized_path=None):
        self.path_list = tuple(path_list or [])
        self.redirect_to = redirect_to
        self.matched_domain = matched_domain
        self.matched_static_route = matched_static_route
        self.base_dbstore = base_dbstore
        self.original_path = original_path
        self.normalized_path = normalized_path


class RequestContext(object):
    __slots__ = ('request_kwargs', 'path_resolution', 'suspicious_request')

    def __init__(self, request_kwargs=None, path_resolution=None, suspicious_request=False):
        self.request_kwargs = dict(request_kwargs or {})
        self.path_resolution = path_resolution
        self.suspicious_request = suspicious_request

    def clone_kwargs(self):
        return dict(self.request_kwargs)


class UrlInfo(object):
    def __init__(self, site, url_list=None, request_kwargs=None):
        self.site = site
        self.url_list = url_list
        self.request_args = None
        self.request_kwargs = request_kwargs or dict()
        self.relpath = None
        self.basepath = ''
        self.plugin = None
        path_list = list(url_list)
        first_chunk = path_list[0]
        if first_chunk=='webpages':
            self.pkg = self.site.mainpackage
            self.basepath =  self.site.site_static_dir
        else:
            pkg_obj = self.site.gnrapp.packages[first_chunk]
            if pkg_obj:
                path_list.pop(0)
            else:
                pkg_obj = self.site.gnrapp.packages[self.site.mainpackage]
            if path_list and path_list[0]=='_plugin':
                path_list.pop(0)
                self.plugin = path_list.pop(0)
                self.basepath= pkg_obj.plugins[self.plugin].webpages_path
            else:
                if isinstance(pkg_obj, GnrPackage):
                    self.basepath =  os.path.join(pkg_obj.packageFolder,'webpages')
                else:
                    self.request_args = []
                    return 
            self.pkg = pkg_obj.id
        mobilepath = None
        if self.request_kwargs.pop('_mobile',False):
            basepath= self.basepath.replace('webpages','webpages_mobile')
            if os.path.exists(basepath):
                mobilepath = basepath
        pathfile_cache = self.site.pathfile_cache
        for basepath in (mobilepath, self.basepath):
            if not basepath:
                continue
            path_list_copy = list(path_list)
            currpath = []
            while path_list_copy:
                currpath.append(path_list_copy.pop(0))
                searchpath = os.path.splitext(os.path.join(basepath,*currpath))[0]
                cached_path = pathfile_cache.get(searchpath)
                if cached_path is None:
                    cached_path = '%s.py' %searchpath
                    if not os.path.isfile(cached_path):
                        cached_path = False
                    pathfile_cache[searchpath] = cached_path
                if cached_path:
                    self.relpath = cached_path
                    self.request_args = path_list_copy
                    self.basepath = basepath
                    return
            last_path = os.path.join(basepath,*path_list)
            last_index_path = os.path.join(last_path,'index.py')
            if os.path.isfile(last_index_path):
                pathfile_cache[last_path] = last_index_path
                pathfile_cache[last_index_path.replace('.py','')] = last_index_path
                self.relpath = last_index_path
                self.request_args = []
                self.basepath = basepath
                return
        self.basepath = mobilepath or self.basepath
        self.request_args = path_list


class GnrDomainProxy(object):
    def __init__(self,parent,domain=None,**kwargs):
        self.parent = parent
        self.domain = domain
        self._register = None
        self.attributes = kwargs      

    @property
    def register(self):
        if self._register:
            return self._register
        self._register  = SiteRegisterClient(self.parent.site)
        self.parent.site.checkPendingConnection()
        return self._register 

class GnrDomainHandler(object):
    def __init__(self,site):
        self.site = site
        self.domains = {}

    def __contains__(self, name):
        result = name in self.domains
        if result:
            return result
        self._missing_from_dbstores(name)
        return name in self.domains
    
    def __getitem__(self,name):
        if name not in self.domains:
            self._missing_from_dbstores(name)
        return self.domains.get(name)

    def add(self,domain):
        if domain not in self.domains:
            self.domains[domain] = GnrDomainProxy(self,domain)

    def _missing_from_dbstores(self,domain):
        if domain in self.site.db.dbstores:
            self.add(domain)

class GnrWsgiSite(object):
    """TODO"""

    def __init__(self, script_path, site_name=None, _config=None,
                 _gnrconfig=None, counter=None, noclean=None,
                 options=None, tornado=None, websockets=None,
                 debugpy=False):
        
        global GNRSITE
        GNRSITE = self
        counter = int(counter or '0')
        self.pathfile_cache = {}
        self._currentAuxInstanceNames = {}
        self._currentPages = {}
        self._currentDomains = {}
        self._currentRequests = {}
        self._currentMaintenances = {}
        self.domains = GnrDomainHandler(self)
        abs_script_path = os.path.abspath(script_path)
        self.remote_db = ''
        if site_name and ':' in site_name:
            _,self.remote_db = site_name.split(':',1)
        
        if os.path.isfile(abs_script_path):
            self.site_name = os.path.basename(os.path.dirname(abs_script_path))
        else:
            site_name = site_name or script_path
            if site_name and ':' in site_name:
                site_name,self.remote_db = site_name.split(':',1)
            self.site_name = site_name
            
        self.site_path = PathResolver().site_name_to_path(self.site_name)
        site_parent=(os.path.dirname(self.site_path))

        if site_parent.endswith('sites'):
            self.project_name = os.path.basename(os.path.dirname(site_parent))
        else:
            self.project_name = None
            
        if _gnrconfig:
            self.gnr_config = _gnrconfig
        else:
            self.gnr_config = getGnrConfig(set_environment=True)

        self.config = self.load_site_config()
        self.cache_max_age = int(self.config['wsgi?cache_max_age'] or 5356800)
        self.default_uri = self.config['wsgi?home_uri'] or '/'
        self.rootDomain = '_main_'
        self.domains.add(self.rootDomain)

        # FIXME: ???
        if boolean(self.config['wsgi?static_import_psycopg']):
            try:
                import psycopg2 # noqa: F401
            except Exception:
                pass
            
        if self.default_uri[-1] != '/':
            self.default_uri += '/'
       

        
        self.root_static = self.config['wsgi?root_static']
        self.websockets= boolean(self.config['wsgi?websockets']) or websockets
        self.allConnectionsFolder = os.path.join(self.site_path, 'data', '_connections')
        self.allUsersFolder = os.path.join(self.site_path, 'data', '_users')

        self.homepage = self.config['wsgi?homepage'] or self.default_uri + 'index'
        self.indexpage = self.config['wsgi?homepage'] or '/index'
        self._guest_counter = 0
        self._initExtraFeatures()
        if not self.homepage.startswith('/'):
            self.homepage = '%s%s' % (self.default_uri, self.homepage)
        self.secret = self.config['wsgi?secret'] or 'supersecret'
        self.config['secret'] = self.secret
        self.setDebugAttribute(options)
        self.default_page = self.config['wsgi?default_page'] 
        if not self.default_page and self.debug:
            self.default_page = 'sys/default'
        self.statics = StaticHandlerManager(self)
        self.statics.addAllStatics()
        self.compressedJsPath = None
        self.pages_dir = os.path.join(self.site_path, 'webpages')
        self.site_static_dir = self.config['resources?site'] or '.'
        if self.site_static_dir and not os.path.isabs(self.site_static_dir):
            self.site_static_dir = os.path.normpath(os.path.join(self.site_path, self.site_static_dir))
        self.find_gnrjs_and_dojo()
        self._remote_edit = options.remote_edit if options else None
        self._main_gnrapp = self.build_gnrapp(options=options)
        self.server_locale = self.gnrapp.locale
        self.wsgiapp = self.build_wsgiapp(options=options)
        self.debugpy = debugpy
        logger.debug("Debugpy active: %s", self.debugpy)
        #self.dbstores = self.db.dbstores to remove
        self.resource_loader = ResourceLoader(self)
        self.pwa_handler = PWAHandler(self)
        self.auth_token_generator = AuthTokenGenerator(self.external_secret)
        self.page_factory_lock = RLock()
        self.webtools = self.resource_loader.find_webtools()
        self.webtools_static_routes = {}
        for tool_name, tool_impl in self.webtools.items():
            alias_url = getattr(tool_impl.__call__, "alias_url", None)
            if alias_url:
                self.webtools_static_routes[alias_url] = tool_name
        self.static_routes = {'favicon.ico':'_site/favicon.ico',
                              '_pwa_worker.js':'_rsrc/common/pwa/worker.js'}

        # this is needed, don't remove - if removed, the register
        # is not initialized, since self.register is a property
        # and it initialze the register itself.
        #self.register
        
        if counter == 0 and self.debug:
            self.onInited(clean=not noclean)
            
        if counter == 0 and options and options.source_instance:
            self.gnrapp.importFromSourceInstance(options.source_instance)
            self.db.commit()
            logger.info('End of import')

        cleanup = self.custom_config.getAttr('cleanup') or dict()
        self.cleanup_interval = int(cleanup.get('interval') or 120)
        self.page_max_age = int(cleanup.get('page_max_age') or 120)
        self.connection_max_age = int(cleanup.get('connection_max_age')or 600)
        self.db.closeConnection()

    @property
    def multidomain(self):
        return self.db.multidomain

    @property
    def guest_counter(self):
        """TODO"""
        # this construct seems to be unused
        self._guest_counter += 1
        return self._guest_counter

    def log_print(self, msg, code=None):
        """
        Internal logging invocation 
        :param msg: The log message
        :param code: The method which invoked the log
        """
        if not code:
            code = "OTHER"
        logger.debug('%s: %s', code, msg)

    def setDebugAttribute(self, options):
        self.force_debug = False
        if options:
            self.debug = boolean(options.debug)
            if self.debug:
                self.force_debug = True
        else:
            if boolean(self.config['wsgi?debug']) is not True and (self.config['wsgi?debug'] or '').lower()=='force':
                self.debug = True
                self.force_debug = True
            else:
                self.debug = boolean(self.config['wsgi?debug'])


    def __call__(self, environ, start_response):
        return self.wsgiapp(environ, start_response)

    @property
    def db(self):
        return self.gnrapp.db
    
    @property
    def gnrapp(self):
        if self.currentAuxInstanceName:
            return self._main_gnrapp.getAuxInstance(self.currentAuxInstanceName)
        return self._main_gnrapp

    @property
    def services_handler(self):
        if not hasattr(self,'_services_handler'):
            self._services_handler = ServiceHandler(self)
        return self._services_handler
    
    @property
    def mainpackage(self):
        return self.config['wsgi?mainpackage'] or self.gnrapp.config['packages?main'] or self.gnrapp.packages.keys()[-1]
    
    def getAuxInstance(self,name):
        return self._main_gnrapp.getAuxInstance(name)

    def siteConfigPath(self):
        siteConfigPath = os.path.join(self.site_path,'siteconfig.xml')
        if os.path.exists(siteConfigPath):
            return siteConfigPath
        siteConfigPath = os.path.join(self.getInstanceFolder(),'config','siteconfig.xml')
        if os.path.exists(siteConfigPath):
            return siteConfigPath

    def getInstanceFolder(self):
        return PathResolver().instance_name_to_path(self.site_name)

    @property
    def wsk(self):
        if not self.websockets:
            return
        if not hasattr(self,'_wsk'):
            wsk = WsgiWebSocketHandler(self)
            if self.websockets=='required' or wsk.checkSocket():
                self._wsk = wsk
            else:
                self.websockets = False
                return
        return self._wsk

    @property
    def mainregister(self):
        return self._get_register(self.rootDomain)
    
    @property
    def register(self):
        if not self.currentDomain:
            logger.error('missing domain')
            self.currentDomain = '_main_'
        return self._get_register(self.currentDomain)

    def _get_register(self,domain):
        if domain in self.domains:
            return self.domains[domain].register
  
    def getSubscribedTables(self,tables):
        if self.domains[self.currentDomain].register:
            return self.register.filter_subscribed_tables(tables,register_name='page')

    @property
    def connectionLogEnabled(self):
        if not hasattr(self,'_connectionLogEnabled'):
            if not self.db.package('adm'):
                self._connectionLogEnabled = False
            else:
                self._connectionLogEnabled = self.getPreference('dev.connection_log_enabled',pkg='adm')
        return self._connectionLogEnabled

    @property
    def connectionDebugEnabled(self):
        if not hasattr(self, '_connectionDebugEnabled'):
            debug_flag = self.config.getItem('debug?connection')
            self._connectionDebugEnabled = boolean(debug_flag) if debug_flag is not None else False
        return self._connectionDebugEnabled

    def log_connection_debug(self, message, payload=None):
        if not self.connectionDebugEnabled:
            return
        payload = payload or {}
        payload.setdefault('domain', self.currentDomain)
        payload.setdefault('site', self.site_name)
        logger.debug('connection.%s %s', message, payload)


    @property
    def remote_edit(self):
        return self._remote_edit

    def _initExtraFeatures(self):
        self.extraFeatures = defaultdict(lambda:None)
        extra = self.config['extra']
        if extra:
            for n in extra:
                if n.label.startswith('wsk_') and not self.websockets:
                    #exclude wsk options if websockets are not activated
                    continue
                attr = dict(n.attr)
                if boolean(attr.pop('enabled',False)):
                    self.extraFeatures[n.label] = True
                    for k,v in list(attr.items()):
                        self.extraFeatures['%s_%s' %(n.label,k)] = v

    def serviceList(self, service_type):
        return self.services_handler(service_type).configurations()


    def getService(self, service_type=None, service_name=None, **kwargs):
        logger.debug("Requesting service type %s with name %s", service_type, service_name)
        return self.services_handler.getService(service_type=service_type,
                                                service_name=service_name or service_type,
                                                **kwargs)

    def addStatic(self, static_handler_factory, **kwargs):
        """TODO

        :param service_handler_factory: TODO"""
        return self.statics.add(static_handler_factory, **kwargs)

    def getVolumeService(self, storage_name=None):
        sitevolumes = self.config.getItem('volumes')
        if sitevolumes and storage_name in sitevolumes:
            vpath = sitevolumes.getAttr(storage_name,'path')
        else:
            vpath = storage_name
        volume_path = expandpath(os.path.join(self.site_static_dir,vpath))
        return self.getService(service_type='storage',service_name=storage_name
            ,implementation='local',base_path=volume_path)

    def storagePath(self, storage_name, storage_path):
        if storage_name == 'user':
            return '%s/%s'%(self.currentPage.user, storage_path)
        elif storage_name == 'conn':
            return '%s/%s'%(self.currentPage.connection_id, storage_path)
        elif storage_name == 'page':
            return '%s/%s/%s'% (self.currentPage.connection_id, self.currentPage.page_id, storage_path)
        return storage_path

    def storage(self, storage_name,**kwargs):
        storage = self.getService(service_type='storage',service_name=storage_name)
        if not storage: 
            storage = self.getVolumeService(storage_name=storage_name)
        return storage

    def storageNode(self,*args,**kwargs):
        if isinstance(args[0], StorageNode):
            if args[1:]:
                return self.storageNode(args[0].fullpath, args[1:])
            else:
                return args[0]
        path = '/'.join(args)
        if not ':' in path: 
            path = '_raw_:%s'%path
        if path.startswith('http://') or path.startswith('https://'):
            path = '_http_:%s'%path
        service_name, storage_path = path.split(':',1)
        storage_path = storage_path.lstrip('/')
        if service_name == 'vol':       
            #for legacy path
            service_name, storage_path = storage_path.replace(':','/').split('/', 1) 
        service = self.storage(service_name)
        if kwargs.pop('_adapt', True):
            storage_path = self.storagePath(service_name, storage_path)
        if not service: return
        autocreate = kwargs.pop('autocreate', False)
        must_exist = kwargs.pop('must_exist', False)
        version = kwargs.pop('version', None)

        mode = kwargs.pop('mode', None)

        return StorageNode(parent=self, path=storage_path, service=service,
            autocreate=autocreate, must_exist=must_exist, mode=mode,version=version)

    def build_lazydoc(self,lazydoc,fullpath=None,temp_dbstore=None,**kwargs):
        ext = os.path.splitext(fullpath)[1]
        ext = ext.replace('.','') if ext else None 
        if lazydoc.startswith('service:'):
            return  self.getService(lazydoc.split(':')[1])(fullpath=fullpath) is not False
        table,pkey,method = gnrstring.splitAndStrip(lazydoc,sep=',',fixed=3)
        dflt_method = 'create_cached_document_%s' %ext if ext else 'create_cached_document'
        m = getattr(self.db.table(table),(method or dflt_method),None)
        if m:
            self.currentPage = self.dummyPage
            if temp_dbstore:
                self.currentPage.dbstore = temp_dbstore
                self.currentPage.db.currentEnv['storename'] = temp_dbstore
            result = m(pkey)
            return result is not False

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
    
    def pathListFromUrl(self, url):
        "Returns path_list from given url"
        parsed_url = urlsplit(url)
        path_list = parsed_url.path.split('/')
        return list(filter(None, path_list))

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
            exists = self.build_lazydoc(kwargs['_lazydoc'],fullpath=storageNode.internal_path,**kwargs) 
            exists = exists and storageNode.exists

        # WHY THIS?
        self.db.closeConnection()
        if not exists:
            if kwargs.get('_lazydoc'):
                headers = []
                start_response('200 OK', headers)
                return ['']
            return self.not_found_exception(environ, start_response)
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
        static_handler = self.getStatic(static_name)
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
            args = (self.currentPage.user,) + args #comma does matter
        elif static_name == 'conn':
            args = (self.currentPage.connection_id,) + args
        elif static_name == 'page':
            args = (self.currentPage.connection_id, self.currentPage.page_id) + args
        return args

    def getStatic(self, static_name):
        """TODO

        :param static_name: TODO"""
        return self.statics.get(static_name)

    def getApiKeys(self,name):
        node = self.gnrapp.config.getNode(f'api_keys.{name}')
        if node:
            return node.attr

    def exception(self, message):
        """TODO

        :param message: TODO"""
        localizerKw=None
        if self.currentPage and hasattr(self.currentPage, 'localizerKw'):
            localizerKw = self.currentPage.localizerKw
        return  GnrSiteException(message=message,localizerKw=localizerKw)

    def connFolderRemove(self, connection_id=None):
        """
        remove all connection folder to the given connection_id

        if not provide, it will delete all the connection folders
        for connections that do not exist in the register
        """
        if connection_id:
            logger.info("Purging connection folder %s", connection_id)
            shutil.rmtree(os.path.join(self.allConnectionsFolder, connection_id), ignore_errors=True)
        else:
            logger.info("Purging connection folders")
            live_connections=self.register.connections()
            
            connections_folder = self.allConnectionsFolder
            connection_to_remove=[conn_id for conn_id in os.listdir(connections_folder) if conn_id not in live_connections and os.path.isdir(os.path.join(connections_folder, conn_id))]
            for conn_id in connection_to_remove:
                self.connFolderRemove(conn_id)
        

    def onInited(self, clean):
        """TODO

        :param clean: TODO"""
        if clean:
            logger.info("Purging connection folders")
            self.dropConnectionFolder()
            self.initializePackages()

    def on_reloader_restart(self):
        """TODO"""
        #there is no reason to inform siteregister that a process is restarted
        # it seems nobody calls it
        #self.register.on_reloader_restart()
        #self.shared_data.dump()
        pass
    
    def on_site_stop(self):
        """TODO"""
        #self.register.on_site_stop()
        #there is no reason to inform siteregister that a process is stopped
        pass
        


    def initializePackages(self):
        """TODO"""
        self.gnrapp.pkgBroadcast('onSiteInited')

    def resource_name_to_path(self, res_id, safe=True):
        """TODO

        :param res_id: TODO
        :param safe: boolean. TODO"""
        project_resource_path = os.path.join(self.site_path, '..', '..', 'resources', res_id)
        if os.path.isdir(project_resource_path):
            return project_resource_path
        if 'resources' in self.gnr_config['gnr.environment_xml']:
            for path in self.gnr_config['gnr.environment_xml'].digest('resources:#a.path'):
                res_path = expandpath(os.path.join(path, res_id))
                if os.path.isdir(res_path):
                    return res_path
        if safe:
            raise Exception('Error: resource %s not found' % res_id)


    def getUrlInfo(self,path_list,request_kwargs=None,default_path=None):
        info = UrlInfo(self,path_list,request_kwargs)
        if not info.relpath and default_path:
            dirpath=os.path.join(info.basepath,*info.request_args)
            if not os.path.isdir(dirpath):
                return info
            default_info = UrlInfo(self,default_path,request_kwargs)
            default_info.request_args = path_list
            logger.warning('using default_path')
            return default_info
        return info

    def find_gnrjs_and_dojo(self):
        """TODO"""
        self.dojo_path = {}
        self.gnr_path = {}
        for lib, path, cdn in self.gnr_config['gnr.environment_xml.static'].digest('js:#k,#a.path,#a.cdn'):
            if lib.startswith('dojo_'):
                self.dojo_path[lib[5:]] = path
            elif lib.startswith('gnr_'):
                self.gnr_path[lib[4:]] = path

    def load_site_config(self,external_site=None):
        """TODO"""
        return PathResolver().get_siteconfig(external_site or self.site_name)

    def external_site_config(self,sitename):
        return self.load_site_config(external_site=sitename)

    @property
    def custom_config(self):
        if not getattr(self,'_custom_config',None):
            custom_config = Bag(self.config)
            preferenceConfig = self.getPreference(path='site_config',pkg='sys')
            if preferenceConfig is not None and preferenceConfig != '':
                for pathlist,node in preferenceConfig.getIndex():
                    v = node.value
                    attr = node.attr
                    currnode = custom_config.getNode(pathlist,autocreate=True)
                    for k,v in list(attr.items()):
                        if v not in ('',None):
                            currnode.attr[k] = v
                    if v and not isinstance(v,Bag):
                        currnode.value = v
            self._custom_config = custom_config
        return self._custom_config

    @property
    def locale(self):
        if self.currentPage:
            return self.currentPage.locale
        return self.server_locale

    def getPackageFolder(self,pkg):
        return self.gnrapp.packages[pkg].packageFolder

    def callExternalUrl(self,url,method=None,**kwargs):
        kwargs = kwargs or dict()
        for k in kwargs:
            kwargs[k] = self.gnrapp.catalog.asTypedText(kwargs[k])
        if method:
            url = '%s/%s' %(url,method)
        url= urllib.request.urlopen(url,urllib.parse.urlencode(kwargs))
        return url.read()

    def callGnrRpcUrl(self,url,method,*args,**kwargs):
        kwargs = kwargs or dict()
        for k in kwargs:
            kwargs[k] = self.gnrapp.catalog.asTypedText(kwargs[k])
        urlargs = [url,method]+list(args)
        url = '/'.join(urlargs)
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, headers=headers, data=kwargs)
        return self.gnrapp.catalog.fromTypedText(response.text)

    def writeException(self, exception=None, traceback=None):
        try:
            page = self.currentPage
            user, user_ip, user_agent = (page.user, page.user_ip, page.user_agent) if page else (None, None, None)
            return self.db.table('sys.error').writeException(description=str(exception),
                                                      traceback=traceback,
                                                      user=user,
                                                      user_ip=user_ip,
                                                      user_agent=user_agent)
        except Exception as writingErrorException:
            logger.exception('\n ####writingErrorException %s for exception %s' %(str(writingErrorException),str(exception)))

    @public_method
    def writeError(self, description=None,error_type=None, **kwargs):
        try:
            page = self.currentPage
            user, user_ip, user_agent = (page.user, page.user_ip, page.user_agent) if page else (None, None, None)
            self.db.table('sys.error').writeError(description=description,error_type=error_type,user=user,user_ip=user_ip,user_agent=user_agent,**kwargs)
        except Exception as e:
            logger.exception(str(e))
            pass

    def loadResource(self, pkg, *path):
        """TODO

        :param pkg: the :ref:`package <packages>` object
        :param *path: TODO"""
        return self.resource_loader.loadResource(*path, pkg=pkg)

    def _get_currentDomain(self):
        """property currentDomain it returns the page currently used in this thread"""
        return self._currentDomains.get(_thread.get_ident())

    def _set_currentDomain(self, domain):
        """set currentDomain for this thread"""
        self._currentDomains[_thread.get_ident()] = domain

    currentDomain = property(_get_currentDomain, _set_currentDomain)




    def handle_path_list(self, path_info, request_kwargs=None):
        """Return the path segments and eventual redirect target for the request."""
        resolution = None
        request = getattr(self, 'currentRequest', None)
        if request is not None and getattr(request, 'path', None) == path_info:
            request_context = self._ensure_request_context()
            if request_context:
                resolution = request_context.path_resolution
        if resolution is None:
            resolution = self._resolve_path_info(path_info)
        self._apply_resolution_to_request(resolution, request_kwargs)
        return list(resolution.path_list), resolution.redirect_to

    def _ensure_request_context(self):
        context_store = self._current_request_context(create=True)
        request_context = context_store.get('request_context') if context_store is not None else None
        if request_context:
            return request_context
        request = getattr(self, 'currentRequest', None)
        if request is None:
            return None
        request_kwargs = self.parse_kwargs(self.parse_request_params(request))
        resolution = self._resolve_path_info(request.path)
        self._apply_resolution_to_request(resolution, request_kwargs)
        suspicious_request = self._detect_suspicious_request(resolution)
        request_context = RequestContext(
            request_kwargs=request_kwargs,
            path_resolution=resolution,
            suspicious_request=suspicious_request
        )
        if context_store is not None:
            context_store['request_context'] = request_context
        return request_context

    def _detect_suspicious_request(self, resolution):
        if not self.multidomain:
            return False
        if resolution.matched_domain:
            return False
        if resolution.matched_static_route or resolution.base_dbstore:
            return False
        normalized_segments = resolution.normalized_path.strip('/').split('/') if resolution.normalized_path else []
        if not normalized_segments:
            return False
        first_segment = normalized_segments[0]
        if first_segment in self.domains:
            return False
        if first_segment in self.storageTypes:
            return False
        if first_segment in self.static_routes:
            return False
        allowed_root_segments = {'_ping', '_beacon', '_pwa_manifest.json'}
        allowed_prefixes = ('_tools',)
        if first_segment in allowed_root_segments:
            return False
        if any(first_segment.startswith(prefix) for prefix in allowed_prefixes):
            return False
        return True

    def _current_request_context(self, create=False):
        request = getattr(self, 'currentRequest', None)
        if request is None or not hasattr(request, 'environ'):
            return {} if create else None
        key = '__gnr_request_context__'
        environ = request.environ
        if create:
            return environ.setdefault(key, {})
        return environ.get(key)

    def _apply_resolution_to_request(self, resolution, request_kwargs):
        matched_domain = resolution.matched_domain or self.rootDomain
        self.currentDomain = matched_domain
        if request_kwargs is not None and resolution.base_dbstore:
            request_kwargs['base_dbstore'] = resolution.base_dbstore
        if hasattr(self, 'db') and getattr(self.db, 'currentEnv', None) is not None:
            self.db.currentEnv['domainName'] = matched_domain

    def _resolve_path_info(self, path_info):
        normalized_path = self._normalize_path_info(path_info)
        path_list = self._split_path_list(normalized_path)
        if not path_list:
            return PathResolution(
                path_list,
                matched_domain=self.currentDomain,
                original_path=path_info,
                normalized_path=normalized_path
            )
        static_target = self._resolve_static_route(path_list)
        if static_target:
            return PathResolution(
                static_target,
                matched_static_route=path_list[0],
                matched_domain=self.currentDomain,
                original_path=path_info,
                normalized_path=normalized_path
            )
        resolved_path_list, redirect_to, matched_domain, base_dbstore = self._resolve_multidomain_path(
            normalized_path, path_list
        )
        return PathResolution(
            resolved_path_list,
            redirect_to=redirect_to,
            matched_domain=matched_domain,
            base_dbstore=base_dbstore,
            original_path=path_info,
            normalized_path=normalized_path
        )

    def _normalize_path_info(self, path_info):
        if path_info in ('/', ''):
            return self.indexpage
        return path_info

    def _split_path_list(self, path_info):
        return [p for p in path_info.strip('/').split('/') if p]

    def _resolve_static_route(self, path_list):
        first_segment = path_list[0]
        if first_segment in self.static_routes:
            return self.static_routes[first_segment].split('/')
        return None

    def _resolve_multidomain_path(self, path_info, path_list):
        redirect_to = None
        matched_domain = None
        base_dbstore = None
        if self.multidomain and path_list:
            first_segment = path_list[0]
            if first_segment in self.domains:
                if path_list[-1] == first_segment and not path_info.endswith('/'):
                    redirect_to = f'{path_info}/'
                else:
                    self.currentDomain = first_segment
                    matched_domain = first_segment
                    if matched_domain != self.rootDomain:
                        base_dbstore = matched_domain
                    path_list = path_list[1:]
            elif first_segment not in self.storageTypes:
                logger.warning('Multidomain site with first segment without domain %s', first_segment)
        return path_list, redirect_to, matched_domain, base_dbstore

    def _get_home_uri(self):
        if self.multidomain:
            return f'{self.default_uri}{self.currentDomain}/'
        if self.currentPage and self.currentPage.dbstore:
            return f'{self.default_uri}{self.currentPage.dbstore}/'
        else:
            return self.default_uri

    home_uri = property(_get_home_uri)

    def parse_request_params(self, request):
        """TODO

        :param params: TODO"""
        out_dict = dict()
        for source in (request.values, request.files):
            for name,value in source.lists():
                try:
                    name = str(name)
                    if len(value)==1:
                        out_dict[name]=value[0]
                    else:
                        out_dict[name] = value
                except UnicodeDecodeError:
                    pass
        return out_dict

    @property
    def dummyPage(self):
        environ_builder = EnvironBuilder(method='GET',base_url=self.external_host,path='/sys/headless')
        request = Request(environ_builder.get_environ())
        response = Response()
        page = self.resource_loader(['sys', 'headless'], request, response)
        page.locale = self.server_locale
        return page

    def virtualPage(self, table=None,table_resources=None,py_requires=None):
        page = self.dummyPage
        if table and table_resources:
            for path in table_resources.split(','):
                page.mixinTableResource(table=table,path=path)

        if py_requires:
            for path in py_requires.split(','):
                page.mixinComponent(path)
        return page

    @property
    def currentDomainIdentifier(self):
        return self.get_domainIdentifier(self.currentDomain)
    
    def get_domainIdentifier(self,domain):
        return self.site_name if not self.multidomain else f'{self.site_name}_{domain}'

    @property
    def isInMaintenance(self):
        request = self.currentRequest
        request_context = self._ensure_request_context()
        if not request_context:
            return False
        if request_context.suspicious_request:
            return False
        resolution = request_context.path_resolution
        path_list = list(resolution.path_list)
        request_kwargs = request_context.clone_kwargs()
        first_segment = path_list[0] if path_list else ''
        if request_kwargs.get('forcedlogin') or (first_segment.startswith('_') and first_segment!='_ping'):
            return False
        elif 'page_id' in request_kwargs:
            self.currentMaintenance = 'maintenance' if self.register.pageInMaintenance(page_id=request_kwargs['page_id'],register_name='page') else None
            if not self.currentMaintenance or (first_segment == '_ping'):
                return False
            return True
        else:
            r = GnrWebRequest(request)
            c = r.get_cookie(self.currentDomainIdentifier,'marshal', secret=self.config['secret'])
            user = c.get('user') if c else None
            return self.register.isInMaintenance(user)
        

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)
        self.currentDomain = self.rootDomain
        self.currentRequest.max_form_memory_size = 100_000_000
        request_context = self._ensure_request_context()
        if request_context and request_context.suspicious_request:
            self.log_connection_debug('request.suspicious', dict(
                path=request_context.path_resolution.original_path,
                normalized_path=request_context.path_resolution.normalized_path,
                user_agent=self.currentRequest.user_agent.string if self.currentRequest.user_agent else None,
                environ_host=environ.get('HTTP_HOST'),
                referer=environ.get('HTTP_REFERER')
            ))
            return self.not_found_exception(environ, start_response, debug_message='suspicious root request')
        if self.isInMaintenance:
            return self.maintenanceDispatcher(environ, start_response)
        else:
            try:
                return self._dispatcher(environ, start_response)
            except self.register.errors.ConnectionClosedError:
                self.currentMaintenance = 'register_error'
                self.domains[self.currentDomain].register = None
                return self.maintenanceDispatcher(environ, start_response)
            except Exception as e:
                page = self.currentPage
                if self.debug and ((page and page.isDeveloper()) or self.force_debug):
                    raise
                self.writeException(exception=e,traceback=tracebackBag())
                exc = HTTPInternalServerError(
                    'Internal server error',
                    comment='SCRIPT_NAME=%r; PATH_INFO=%r;'
                    % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO')))
                return exc(environ, start_response)

    def maintenanceDispatcher(self,environ, start_response):
        request = self.currentRequest
        response = Response()
        response.mimetype = 'text/html'
        request_context = self._ensure_request_context()
        resolution = request_context.path_resolution if request_context else self._resolve_path_info(request.path)
        request_kwargs = request_context.clone_kwargs() if request_context else {}
        path_list = list(resolution.path_list)
        if (path_list and path_list[0].startswith('_')) or ('method' in request_kwargs or 'rpc' in request_kwargs or '_plugin' in request_kwargs):
            response = self.setResultInResponse('maintenance', response, info_GnrSiteMaintenance=self.currentMaintenance)
            return response(environ, start_response)
        else:
            return self.serve_htmlPage('html_pages/maintenance.html', environ, start_response)

    @property
    def external_host(self):
        page = self.currentPage
        if (page and hasattr(page,'request')):
            external_host = page.request.host_url 
        else:
            external_host = self.configurationItem('wsgi?external_host',mandatory=True)
        external_host = (external_host or '').rstrip('/')
        if self.multidomain:
            external_host = f'{external_host}/{self.currentDomain}'
        return external_host
    

    @property
    def external_secret(self):
        return getEnvironmentItem('external_secret',default=getUuid(),update=True)
        
    def configurationItem(self,path,mandatory=False):
        result = self.config[path]
        if mandatory and result is None:
            logger.warning('Missing mandatory configuration item: %s' %path)
        return result
    
    def pwa_config(self):
        pwa = self.config['pwa']
        if pwa:
            result = {}
            for k,v in pwa.items():
                result[k] = v.replace('\t','').replace('\n','').replace('\r','').strip()
            return result
        return self.config.getAttr('pwa')

    @functools.lru_cache
    def lookup_webtools_static_route(self, request_path):
        result = self.webtools_static_routes.get(request_path, None)
        if not result and ('.well-known' in request_path):
            raise HTTPNotFound('Missing well-known')
        return result
    
    def _dispatcher(self, environ, start_response):
        """Main :ref:`wsgi` dispatcher, serve static files and
        self.createWebpage for :ref:`gnrcustomwebpage`
        :param environ: TODO
        :param start_response: TODO"""
        
        self.currentPage = None
        t = time()
        request = self.currentRequest
        response = Response()
        response.headers.add_header("X-PROCESS", str(os.getpid())) #debugging multiprocess in deploy

        # default mime type
        response.mimetype = 'text/html'
        request_context = self._ensure_request_context()
        if request_context:
            request_kwargs = request_context.clone_kwargs()
            resolution = request_context.path_resolution
        else:
            request_kwargs = self.parse_kwargs(self.parse_request_params(request))
            resolution = self._resolve_path_info(request.path)
            self._apply_resolution_to_request(resolution, request_kwargs)
        
        webtool_static_route_handler = self.lookup_webtools_static_route(request.path)
        if webtool_static_route_handler:
            return self.serve_tool(['_tools', webtool_static_route_handler], environ, start_response, **request_kwargs)
        # Url parsing start
        path_list = list(resolution.path_list)
        redirect_to = resolution.redirect_to
        if redirect_to:
            return self.redirect(environ,start_response,location=redirect_to)
        # path_list is never empty
        expiredConnections = self.register.cleanup()
        if expiredConnections:
            self.connectionLog('close',expiredConnections)
        # lookup webtools static routes
        self.currentAuxInstanceName = request_kwargs.get('aux_instance')
        user_agent = request.user_agent.string or ''
        isMobile = len(IS_MOBILE.findall(user_agent))>0
        if isMobile:
            request_kwargs['_mobile'] = True
        request_kwargs.pop('_no_cache_', None)
        download_name = request_kwargs.pop('_download_name_', None)
        #print 'site dispatcher: ',path_list
        if path_list and not self.multidomain:
            self._checkFirstSegment(path_list,request_kwargs)
            self.checkForDbStore(request_kwargs)
        path_list = path_list or ['index']
        first_segment = path_list[0]
        last_segment = path_list[-1]
        # this can be moved.
        if first_segment == '_ping':
            try:
                self.log_print('kwargs: %s' % str(request_kwargs), code='PING')
                result = self.serve_ping(response, environ, start_response, **request_kwargs)
                if not isinstance(result, (bytes,str)):
                    return result
                response = self.setResultInResponse(result, response, info_GnrTime=time() - t,info_GnrSiteMaintenance=self.currentMaintenance)
                self.cleanup()
            except Exception as exc:
                raise
            finally:
                self.cleanup()
            return response(environ, start_response)

        # this can be moved
        if first_segment == '_pwa_manifest.json':
            try:
                result = self.serve_manifest(response, environ, start_response, **request_kwargs)
                if not isinstance(result, (bytes,str)):
                    return result
                response = self.setResultInResponse(result, response)
                self.cleanup()
            except Exception as exc:
                raise
            finally:
                self.cleanup()
            return response(environ, start_response)
        if first_segment == '_beacon':
            try:
                method = request_kwargs.pop('method',None)
                if method:
                    handler = getattr(self,method,None)
                    if handler and hasattr(handler,'beacon'):
                        handler(**request_kwargs)
                self.cleanup()
            except Exception as exc:
                raise
            finally:
                self.cleanup()
            return response(environ, start_response)

        #static elements that doesn't have .py extension in self.root_static
        if self.root_static and not first_segment.startswith('_') and '.' in last_segment and not (':' in first_segment):
            if last_segment.split('.')[-1]!='py':
                path_list = self.root_static.split('/')+path_list
                first_segment = path_list[0]
        storageType = self.storageType(path_list)
        if storageType:
            self.log_print('%s : kwargs: %s' % (path_list, str(request_kwargs)), code='STORAGE')
            return self.storageDispatcher(path_list, environ, start_response, 
                                                        storageType=storageType, **request_kwargs)
        elif first_segment.startswith('_tools'):
            self.log_print('%s : kwargs: %s' % (path_list, str(request_kwargs)), code='TOOLS')
            return self.serve_tool(path_list, environ, start_response, **request_kwargs)
        elif first_segment.startswith('_'):
            self.log_print('%s : kwargs: %s' % (path_list, str(request_kwargs)), code='STATIC')
            try:
                return self.statics.static_dispatcher(path_list, environ, start_response, **request_kwargs)
            except GnrDebugException as exc:
                raise
            except Exception as exc:
                return self.not_found_exception(environ,start_response)
        else:
            self.log_print('%s : kwargs: %s' % (path_list, str(request_kwargs)), code='RESOURCE')
            try:
                page = self.resource_loader(path_list, request, response, environ=environ,request_kwargs=request_kwargs)
                if page:
                    page.download_name = download_name
            except WSGIHTTPException as exc:
                return exc(environ, start_response)
            except Exception as exc:
                logger.exception("wsgisite.dispatcher: self.resource_loader failed with non-HTTP exception.")
                logger.exception(str(exc))
                raise

            if not (page and page._call_handler):
                return self.not_found_exception(environ, start_response)
            self.currentPage = page
            self.onServingPage(page)
            try:
                result = page()
                if page.download_name:
                    download_name = str(page.download_name)
                    content_type = getattr(page,'forced_mimetype',None) or mimetypes.guess_type(download_name)[0]
                    if content_type:
                        page.response.content_type = content_type
                    page.response.add_header("Content-Disposition", str("attachment; filename=%s" %download_name))

                try:
                    file_types = file, io.IOBase
                except NameError:
                    file_types = (io.IOBase,)
                if isinstance(result, file_types):
                    return self.statics.fileserve(result, environ, start_response,nocache=True,download_name=page.download_name)
            except GnrUnsupportedBrowserException:
                return self.serve_htmlPage('html_pages/unsupported.html', environ, start_response)
            except GnrMaintenanceException:
                return self.serve_htmlPage('html_pages/maintenance.html', environ, start_response)
            except HTTPNotFound:
                return self.serve_htmlPage('html_pages/missing_result.html', environ, start_response)
            finally:
                self.onServedPage(page)
                self.cleanup()
            response = self.setResultInResponse(result, response, info_GnrTime=time() - t,info_GnrSqlTime=page.sql_time,info_GnrSqlCount=page.sql_count,
                                                                info_GnrXMLTime=getattr(page,'xml_deltatime',None),info_GnrXMLSize=getattr(page,'xml_size',None),
                                                                info_GnrSiteMaintenance=self.currentMaintenance,
                                                                forced_headers=page.getForcedHeaders(),
                                                                mimetype=getattr(page,'forced_mimetype',None))

            return response(environ, start_response)

    def serve_htmlPage(self, htmlPageName, environ, start_response):
        uri = self.dummyPage.getResourceUri(htmlPageName)
        if uri:
            path_list = uri[1:].split('/')
            return self.statics.static_dispatcher(path_list, environ, start_response,nocache=True)

    def checkForDbStore(self,request_kwargs):
        for k in ('temp_dbstore','base_dbstore'):
            storename = request_kwargs.get(k)        
            if storename and storename.startswith('instance_'):
                self._registerAuxInstanceDbStore(storename)

    def _checkFirstSegment(self,path_list,request_kwargs):
        first = path_list[0]
        if first.startswith('@'):
            first = first[1:]
            path_list.pop(0)
            if self.gnrapp.config.getNode(f'aux_instances.{first}'):
                request_kwargs['base_dbstore'] = f'instance_{first}'
            else:
                request_kwargs['_subdomain'] = request_kwargs.get('_subdomain') or first
        else:
            if self.db.get_store_parameters(first):
                request_kwargs['base_dbstore'] = path_list.pop(0)
        if request_kwargs.get('_subdomain'):
            self.gnrapp.pkgBroadcast('handleSubdomain',path_list,request_kwargs=request_kwargs)
        temp_dbstore = request_kwargs.get('temp_dbstore','')
        if temp_dbstore and temp_dbstore.startswith('@'):
            request_kwargs['temp_dbstore'] = f'instance_{request_kwargs["temp_dbstore"][1:]}'

    def _registerAuxInstanceDbStore(self,storename):
        instance_name = storename.replace('instance_','')
        auxapp = self.gnrapp.getAuxInstance(instance_name)
        if not auxapp:
            raise Exception('not existing aux instance %s' %instance_name)
        if self.db.get_store_parameters(storename):
            return
        dbattr = auxapp.config.getAttr('db')
        if auxapp.remote_db:
            remote_db_attr = auxapp.config.getAttr('remote_db.%s' %auxapp.remote_db)
            if remote_db_attr:
                remote_db_attr = dict(remote_db_attr)
                ssh_host = remote_db_attr.pop('ssh_host',None)
                if ssh_host:
                    host = ssh_host.split('@')[1] if '@' in ssh_host else ssh_host
                    port = remote_db_attr.get('port')
                    dbattr['remote_host'] = host
                    dbattr['remote_port'] = port
                dbattr.update(remote_db_attr)
        self.db.stores_handler.add_auxstore(storename,dbattr=dbattr)


    @extract_kwargs(info=True)
    def setResultInResponse(self, result, response,info_kwargs=None,forced_headers=None,**kwargs):
        """TODO

        :param result: TODO
        :param response: TODO
        :param totaltime: TODO"""
        if forced_headers:
            for k,v in list(forced_headers.items()):
                response.headers[k] = str(v)
        for k,v in list(info_kwargs.items()):
            if v is not None:
                v=str(v)
                response.headers['X-%s' %k] = v
        if isinstance(result, str):
            #response.mimetype = kwargs.get('mimetype') or 'text/plain'

            response.mimetype = kwargs.get('mimetype') or response.mimetype or 'text/plain'
            logger.debug(f'response mimetipe {response.mimetype} content_type {response.content_type}')
            response.data=result # PendingDeprecationWarning: .unicode_body is deprecated in favour of Response.text
        
        elif isinstance(result, (bytes,str)):
            response.data=result
        elif isinstance(result, Response):
            response = result
        elif callable(result):
            response = result
        return response

    def onServingPage(self, page):
        """TODO

        :param page: TODO"""
        pass

    def onServedPage(self, page):
        """TODO

        :param page: TODO"""
        pass

    @metadata(beacon=True)
    def onClosedPage(self, page_id=None, **kwargs):
        "Drops page when closing"
        self.register.drop_page(page_id)

    def cleanup(self):
        """clean up"""
        debugger = getattr(self.currentPage,'debugger',None)
        if debugger:
            debugger.onClosePage()
        self.currentPage = None
        self.db.closeConnection()

    def serve_tool(self, path_list, environ, start_response, **kwargs):
        """TODO

        :param path_list: TODO
        :param environ: TODO
        :param start_response: TODO"""
        toolname = path_list[1]
        args = path_list[2:]
        tool = self.load_webtool(toolname)
        if not tool:
            return self.not_found_exception(environ, start_response)
        tool.site = self
        response = Response()
        kwargs['environ'] = environ
        kwargs['response'] = response
        result = tool(*args, **kwargs)
        content_type = getattr(tool, 'content_type', 'text/plain')
        response.mimetype = content_type
        headers = getattr(tool, 'headers', [])
        download_name = getattr(tool, 'download_name', None)
        if download_name:
            headers.append(("Content-Disposition", f"attachment; filename={download_name}"))
        for header_name, header_value in headers:
            response.headers[header_name] = header_value
        if isinstance(result, Response):
            response = result
        else:
            response.data=result
        return response(environ, start_response)

    def load_webtool(self, tool_name):
        """TODO

        :param tool_name: the tool name"""
        webtool = self.webtools.get(tool_name)
        if webtool:
            return webtool()

    def request_url(self,environ):
        return Request(environ).url

    def not_found_exception(self, environ, start_response, debug_message=None):
        """TODO

        :param environ: TODO
        :param start_response: add??
        :param debug_message: TODO"""
        exc = HTTPNotFound(
                'The resource at %s could not be found'
                % self.request_url(environ),
                comment='SCRIPT_NAME=%r; PATH_INFO=%r; debug: %s'
                % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
                   debug_message or '(none)'), )
        return exc(environ, start_response)

    def redirect(self, environ, start_response, location=None,temporary=False):
        if temporary:
            exc = HTTPTemporaryRedirect(location=location)
        else:
            exc = HTTPMovedPermanently(location=location)
        return exc(environ, start_response)

    def forbidden_exception(self, environ, start_response, debug_message=None):
        """TODO

        :param environ: TODO
        :param start_response: add??
        :param debug_message: TODO"""
        exc = HTTPForbidden(
                'The resource at %s could not be viewed'
                % self.request_url(environ),
                comment='SCRIPT_NAME=%r; PATH_INFO=%r; debug: %s'
                % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
                   debug_message or '(none)'))
        return exc(environ, start_response)

    def failed_exception(self, message, environ, start_response, debug_message=None):
        """TODO

        :param message: TODO
        :param environ: TODO
        :param start_response: add??
        :param debug_message: TODO"""
        if '%%s' in message:
            message = message % self.request_url(environ)
        exc = HTTPPreconditionFailed(message,
                                     comment='SCRIPT_NAME=%r; PATH_INFO=%r; debug: %s'
                                     % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
                                        debug_message or '(none)'))
        return exc(environ, start_response)

    def client_exception(self, message, environ):
        """TODO

        :param message: TODO
        :param environ: TODO"""
        logger.warning(
            "Client exception: %s | domain=%s | path=%s | query=%s | remote=%s | ua=%s",
            message,
            getattr(self, 'currentDomain', None),
            environ.get('PATH_INFO') if environ else None,
            environ.get('QUERY_STRING') if environ else None,
            environ.get('REMOTE_ADDR') if environ else None,
            environ.get('HTTP_USER_AGENT') if environ else None,
        )
        message = 'ERROR REASON : %s' % message
        exc = HTTPClientError(message,
                              comment='SCRIPT_NAME=%r; PATH_INFO=%r'
                              % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO')))
        return exc

    def build_wsgiapp(self, options=None):
        """Build the wsgiapp callable wrapping self.dispatcher with WSGI middlewares"""
        wsgiapp = self.dispatcher
        if 'sentry' in self.config:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
                from sentry_sdk import set_tags
                set_tags({"genropy_instance": self.site_name})
                sentry_sdk.init(
                    dsn=self.config['sentry?pydsn'],
                    traces_sample_rate=float(self.config['sentry?traces_sample_rate']) if self.config['sentry?traces_sample_rate'] else 1.0,
                    profiles_sample_rate=float(self.config['sentry?profiles_sample_rate']) if self.config['sentry?profiles_sample_rate'] else 1.0)
                wsgiapp = SentryWsgiMiddleware(wsgiapp)
            except Exception as e:
                logger.error(f"Sentry support has been disabled due to configuration errors: {e}")
        return wsgiapp

    def build_gnrapp(self, options=None):
        """Builds the GnrApp associated with this site"""
        instance_path = os.path.join(self.site_path, 'instance')
        if not os.path.isdir(instance_path):
            instance_path = self.getInstanceFolder()
        if not os.path.isdir(instance_path):
            instance_path = self.config['instance?path'] or self.config['instances.#0?path']
        self.instance_path = instance_path
        restorepath = options.restore if options else None
        restorefiles=[]
        if self.remote_db:
            instance_path = '%s:%s' %(instance_path,self.remote_db)
        app = GnrWsgiWebApp(instance_path, site=self,restorepath=restorepath)
        self.config.setItem('instances.app', app, path=instance_path)
        return app

    def onAuthenticated(self, avatar):
        """TODO

        :param avatar: the avatar (user that logs in)"""
        self.gnrapp.pkgBroadcast('onAuthenticated',avatar)

    def checkPendingConnection(self):
        if self.connectionLogEnabled:
            self.db.table('adm.connection').dropExpiredConnections()

    def pageLog(self, event, page_id=None):
        """TODO

        :param event: TODO
        :param page_id: the 22 characters page id"""
        if self.connectionLogEnabled == 'A':
            self.db.table('adm.served_page').pageLog(event, page_id=page_id)

    def connectionLog(self, event, connection_id=None):
        """TODO

        :param event: TODO
        :param connection_id: TODO"""
        if self.connectionLogEnabled:
            self.db.table('adm.connection').connectionLog(event, connection_id=connection_id)

    def setPreference(self, path, data, pkg=''):
        """TODO

        :param path: TODO
        :param data: TODO
        :param pkg: the :ref:`package <packages>` object"""
        if self.db.package('adm'):
            pkg = pkg or self.currentPage.packageId
            self.db.table('adm.preference').setPreference(path, data, pkg=pkg)

    def getPreference(self, path, pkg=None, dflt=None, mandatoryMsg=None):
        """TODO

        :param path: TODO
        :param pkg: the :ref:`package <packages>` object
        :param dflt: TODO"""
        if self.db.package('adm'):
            pkg = pkg or self.currentPage.packageId
            return self.db.table('adm.preference').getPreference(path, pkg=pkg, dflt=dflt, mandatoryMsg=mandatoryMsg)

    def getUserPreference(self, path, pkg=None, dflt=None, username=None):
        """TODO

        :param path: TODO
        :param pkg: the :ref:`package <packages>` object
        :param dflt: TODO
        :param username: TODO"""
        if self.db.package('adm'):
            username = username or self.currentPage.user if self.currentPage else None
            pkg = pkg or self.currentPage.packageId if self.currentPage else None
            return self.db.table('adm.user').getPreference(path=path, pkg=pkg, dflt=dflt, username=username)

    def setUserPreference(self, path, data, pkg=None, username=None):
        """TODO

        :param path: TODO
        :param data: TODO
        :param pkg: the :ref:`package <packages>` object
        :param username: TODO"""
        if self.db.package('adm'):
            pkg = pkg or self.currentPage.packageId
            username = username or self.currentPage.user if self.currentPage else None
            self.db.table('adm.user').setPreference(path, data, pkg=pkg, username=username)

    @property
    def ukeInstanceId(self):
        if not getattr(self,'_ukeInstanceId',None):
            r = self.db.table('uke.instance').getInstanceRecord()
            self._ukeInstanceId = r['id']
            ukeInstance = self.db.application.getAuxInstance('uke')
            if ukeInstance:
                if not ukeInstance.db.table('uke.instance').existsRecord(r['id']):
                    ukeInstance.db.table('uke.instance').insert(r)
                    ukeInstance.db.commit()
        return self._ukeInstanceId

    def dropConnectionFolder(self, connection_id=None):
        """:param connection_id: TODO"""
        pathlist = ['data', '_connections']
        if connection_id:
            pathlist.append(connection_id)
        connectionFolder = os.path.join(self.site_path, *pathlist)
        for root, dirs, files in os.walk(connectionFolder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        if connection_id:
            os.rmdir(connectionFolder)

    def lockRecord(self, page, table, pkey):
        """TODO

        :param page: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param pkey: the record :ref:`primary key <pkey>`"""
        if 'sys' in self.gnrapp.db.packages:
            return self.gnrapp.db.table('sys.locked_record').lockRecord(page, table, pkey)

    def unlockRecord(self, page, table, pkey):
        """TODO

        :param page: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param pkey: the record :ref:`primary key <pkey>`"""
        if 'sys' in self.gnrapp.db.packages:
            return self.gnrapp.db.table('sys.locked_record').unlockRecord(page, table, pkey)

    def clearRecordLocks(self, **kwargs):
        pass


    def onClosePage(self, page):
        """A method called on when a page is closed on the client

        :param page: the :ref:`webpage` being closed"""
        page_id = page.page_id

        self.pageLog('close', page_id=page_id)
        self.clearRecordLocks(page_id=page_id)
        page._closed = True

    def sqlDebugger(self,**kwargs):
        page = self.currentPage
        if page and self.debug and page.debug_sql:
            page.dev.sqlDebugger.output(page, **kwargs)
            page.sql_count = page.sql_count + 1
            page.sql_time = page.sql_time + kwargs.get('delta_time',0)

    def _get_currentPage(self):
        """property currentPage it returns the page currently used in this thread"""
        return self._currentPages.get(_thread.get_ident())

    def _set_currentPage(self, page):
        """set currentPage for this thread"""
        self._currentPages[_thread.get_ident()] = page

    currentPage = property(_get_currentPage, _set_currentPage)

    def _get_currentAuxInstanceName(self):
        """property currentAuxInstanceName it returns the page currently used in this thread"""
        return self._currentAuxInstanceNames.get(_thread.get_ident())

    def _set_currentAuxInstanceName(self, auxInstance):
        """set currentAuxInstanceName for this thread"""
        self._currentAuxInstanceNames[_thread.get_ident()] = auxInstance

    currentAuxInstanceName = property(_get_currentAuxInstanceName, _set_currentAuxInstanceName)


    def _get_currentMaintenance(self):
        """property currentPage it returns the page currently used in this thread"""
        return self._currentMaintenances.get(_thread.get_ident())

    def _set_currentMaintenance(self, page):
        """set currentPage for this thread"""
        self._currentMaintenances[_thread.get_ident()] = page

    currentMaintenance = property(_get_currentMaintenance, _set_currentMaintenance)

    def _get_currentRequest(self):
        """property currentRequest it returns the request currently used in this thread"""
        return self._currentRequests.get(_thread.get_ident())

    def _set_currentRequest(self, request):
        """set currentRequest for this thread"""
        self._currentRequests[_thread.get_ident()] = request

    currentRequest = property(_get_currentRequest, _set_currentRequest)

    def callTableScript(self, page=None, table=None, respath=None, class_name=None, runKwargs=None, **kwargs):
        """Call a script from a table's resources (e.g: ``_resources/tables/<table>/<respath>``).

        This is typically used to customize prints and batch jobs for a particular installation

        :param page: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param respath: TODO
        :param class_name: TODO
        :param runKwargs: TODO"""
        script = self.loadTableScript(page=page, table=table, respath=respath, class_name=class_name)
        if runKwargs:
            for k, v in list(runKwargs.items()):
                kwargs[str(k)] = v
        result = script(**kwargs)
        return result

    def loadTableScript(self, page=None, table=None, respath=None, class_name=None,**kwargs):
        """TODO

        :param page: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param respath: TODO
        :param class_name: TODO"""
        return self.resource_loader.loadTableScript(page=page, table=table, respath=respath, class_name=class_name,**kwargs)

    def _get_resources(self):
        if not hasattr(self, '_resources'):
            self._resources = self.resource_loader.site_resources()
        return self._resources

    resources = property(_get_resources)

    def _get_resources_dirs(self):
        if not hasattr(self, '_resources_dirs'):
            self._resources_dirs = list(self.resources.values())
            self._resources_dirs.reverse()
        return self._resources_dirs

    resources_dirs = property(_get_resources_dirs)

    def pkg_page_url(self, pkg, *args):
        """TODO

        :param pkg: the :ref:`package <packages>` object"""
        return ('%s%s/%s' % (self.home_uri, pkg, '/'.join(args))).replace('//', '/')

    def webtools_url(self, tool, **kwargs):
        """TODO

        :param tool: TODO"""
        kwargs_string = '&'.join(['%s=%s' % (k, v) for k, v in list(kwargs.items())])
        return '%s%s_tools/%s?%s' % (self.external_host, self.home_uri, tool, kwargs_string)

    def serve_ping(self, response, environ, start_response, page_id=None, reason=None, **kwargs):
        response.content_type = "text/xml"
        currentDomain = self.currentDomain
        result = self.register.handle_ping(page_id=page_id,reason=reason,**kwargs)
        if result is False:
            return self.failed_exception('no longer existing page %s in domain %s' % (page_id,currentDomain), environ, start_response)
        else:
            return result.toXml(unresolved=True, omitUnknownTypes=True)

    def serve_manifest(self, response, environ, start_response, page_id=None, reason=None, **kwargs):
        response.content_type = "application/json"
        return self.pwa_handler.manifest()

    def parse_kwargs(self, kwargs):
        """TODO
        :param kwargs: the kw arguments
        """
        catalog = self.gnrapp.catalog
        result = dict()
        for k, v in list(kwargs.items()):
            k = k.strip()
            if isinstance(v, (bytes,str)):
                try:
                    v = catalog.fromTypedText(v)
                    result[k] = v
                except Exception as e:
                    raise
            else:
                result[k] = v
        return result

    @deprecated
    def site_static_path(self, *args):
        """.. warning:: deprecated since version 0.7"""
        return self.storage('site').path(*args)

    @deprecated
    def site_static_url(self, *args):
        """.. warning:: deprecated since version 0.7"""
        return self.storage('site').url(*args)


    def shellCall(self,*args):
        return subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]

    def extractTextContent(self, filepath=None):
        filename,ext = os.path.splitext(filepath)
        tifname = '%s.tif' %filename
        txtname = '%s.txt' %filename
        try:
            self.shellCall('convert','-density','300',filepath,'-depth','8',tifname)
            self.shellCall('tesseract', tifname, filename)
        except Exception:
            logger.warning('missing tesseract in this installation')
            return
        result = ''
        if not os.path.isfile(txtname):
            return
        with open(txtname,'r') as f:
            result = f.read()
        if os.path.exists(tifname):
            os.remove(tifname)
        if os.path.exists(txtname):
            os.remove(txtname)
        return result

    def uploadFile(self,file_handle=None,dataUrl=None,filename=None,uploadPath=None):
        if file_handle is not None:
            f = file_handle.stream
            content = f.read()
            original_filename = os.path.basename(file_handle.filename)
            original_ext = os.path.splitext(original_filename)[1]
            filename = filename or original_filename
        elif dataUrl:
            import base64
            dataUrlPattern = re.compile('data:(.*);base64,(.*)$')
            g= dataUrlPattern.match(dataUrl)#.group(2)
            mimetype,base64Content = g.groups()
            original_ext = mimetypes.guess_extension(mimetype)
            content = base64.b64decode(base64Content)
        else:
            return None,None
        file_ext = os.path.splitext(filename)[1]
        if not file_ext:
            filename = '%s%s' %(filename,original_ext)
            file_ext = original_ext
        file_node = self.storageNode(uploadPath, filename,autocreate=-1)
        file_path = file_node.fullpath
        file_url = file_node.internal_url()
        with file_node.open(mode='wb') as outfile:
            outfile.write(content)
        return file_path,file_url

    def zipFiles(self, file_list=None, zipPath=None):
        """Allow to zip one or more files

        :param file_list: a string with the files names to be zipped
        :param zipPath: the result path of the zipped file"""
        import zipfile
        zipresult = self.storageNode(zipPath)
        if isinstance(file_list, str):
            file_list = file_list.split(',')
        with zipresult.open(mode='wb') as zipresult:
            zip_archive = zipfile.ZipFile(zipresult, mode='w', compression=zipfile.ZIP_DEFLATED,allowZip64=True)
            for fpath in file_list:
                newname = None
                if isinstance(fpath,tuple):
                    fpath,newname = fpath
                fpath = self.storageNode(fpath)
                if fpath.isdir:
                    self._zipDirectory(fpath,zip_archive)
                    continue
                if not newname:
                    newname = fpath.basename
                with fpath.local_path(mode='r') as local_path:
                    zip_archive.write(local_path, newname)
            zip_archive.close()

    def _zipDirectory(self,path, zip_archive):
        from gnr.lib.services.storage import StorageResolver
        def cb(n):
            if n.attr.get('file_ext')!='directory':
                fpath = self.storageNode(n.attr['abs_path'])
                with fpath.local_path(mode='r') as local_path:
                    zip_archive.write(local_path,n.attr['abs_path'].replace(path.fullpath,''))
                    
        dirres = StorageResolver(path, _page=self.dummyPage)
        dirres().walk(cb,_mode='')

        
    def externalUrl(self, url, _link=False,_signed=None,_expire_ts=None,_expire_minutes=None,**kwargs):
        """TODO

        :param url: TODO"""
        params = urllib.parse.urlencode(kwargs)
        #url = os.url.join(self.homeUrl(), url)
        if url == '':
            url = self.home_uri
        f =  '{}{}' if url.startswith('/') else '{}/{}'
        url = f.format(self.external_host,url)
        if params:
            url = f'{url}?{params}'
        if _signed:
            url = self.auth_token_generator.generate_url(url,expire_ts=_expire_ts,expire_minutes=_expire_minutes)
        if _link:
            return '<a href="%s" target="_blank">%s</a>' %(url,_link if _link is not True else '')
        return url
