#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

#Created by Giovanni Porcari on 2007-03-24.
#Copyright (c) 2007 Softwell. All rights reserved.

import os
import sys
import shutil
import urllib.request, urllib.parse, urllib.error
import _thread
import copy
from time import time
from datetime import timedelta
from mako.lookup import TemplateLookup
from base64 import b64decode
import re
import datetime

from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.core.gnrstring import toText, toJson, concat, jsquote,splitAndStrip,boolean,asDict
from gnr.core.gnrdict import dictExtract
from gnr.web.gnrwebreqresp import GnrWebRequest, GnrWebResponse
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from gnr.web.gnrwebpage_proxy.menuproxy import GnrMenuProxy
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.connection import GnrWebConnection
from gnr.web.gnrwebpage_proxy.serverbatch import GnrWebBatch
from gnr.web.gnrwebpage_proxy.rpc import GnrWebRpc
from gnr.web.gnrwebpage_proxy.developer import GnrWebDeveloper
from gnr.web.gnrwebpage_proxy.gnrpdb import GnrPdbClient
from gnr.web.gnrwebpage_proxy.utils import GnrWebUtils
from gnr.web.gnrwebpage_proxy.pluginhandler import GnrWebPluginHandler
from gnr.web.gnrwebpage_proxy.jstools import GnrWebJSTools
from gnr.web.gnrwebstruct import GnrGridStruct
from gnr.core.gnrlang import getUuid,gnrImport, GnrException, GnrSilentException, tracebackBag
from gnr.core.gnrbag import Bag, BagResolver
from gnr.core.gnrdecorator import public_method,deprecated
from gnr.core.gnrclasses import GnrMixinNotFound

 # DO NOT REMOVE, old code relies on BaseComponent being defined in this file
from gnr.web.gnrbaseclasses import BaseComponent # noqa: F401


from gnr.app.gnrlocalization import GnrLocString

AUTH_OK = 0
AUTH_NOT_LOGGED = 1
AUTH_EXPIRED = 2
AUTH_FORBIDDEN = -1
PAGE_TIMEOUT = 60
PAGE_REFRESH = 20

ATTRIBUTES_SIMPLEWEBPAGE = ('_workdate','_language','_call_args','_call_kwargs','user','connection_id','user_ip','dbstore','user_agent','siteName')



def formulaColumn(*args,**fcpars):
    """add a local formula column"""
    def decore(func):
        fcpars.setdefault('name',func.__name__)
        setattr(func,'mixin_as','formulacolumn_%s' %(func.__name__))
        func.formulaColumn_kw = fcpars
        return func
    return decore
    
class GnrWebPageException(GnrException):
    pass

class GnrUnsupportedBrowserException(GnrException):
    pass

class GnrMaintenanceException(GnrException):
    pass

class GnrSignedTokenException(GnrException):
    pass

class GnrMissingResourceException(GnrException):
    pass

class GnrUserNotAllowed(GnrException):
    code = 'AUTH-001'
    description = '!!Genro Not Allowed Public call'
    caption = "!!User %(user)s is not allowed to call method %(method)s"    

class GnrBasicAuthenticationError(GnrException):
    code = 'AUTH-901'

EXCEPTIONS = {'user_not_allowed': GnrUserNotAllowed,
              'missing_resource': GnrMissingResourceException,
              'unsupported_browser': GnrUnsupportedBrowserException,
              'generic': GnrWebPageException,
              'basic_authentication':GnrBasicAuthenticationError,
              'maintenance': GnrMaintenanceException}

class GnrWebPage(GnrBaseWebPage):
    """Standard class for :ref:`webpages <webpage>`
    
    :param site: TODO
    :param request: TODO
    :param response: TODO
    :param request_kwargs: TODO
    :param request args: TODO
    :param filepath: TODO
    :param packageId: TODO
    :param basename: TODO
    :param environ: TODO"""

    proxy_class = GnrBaseProxy
    
    def __init__(self, site=None, request=None, response=None, request_kwargs=None, request_args=None,
                 filepath=None, packageId=None, pluginId=None, basename=None, environ=None, class_info=None,_avoid_module_cache=None):
        self._inited = False
        self._start_time = time()
        self._thread = _thread.get_ident()
        self.workspace = dict()
        self.sql_count = 0
        self.sql_time = 0
        self.site = site
        if self.site.currentPage:
            self._db = self.site.currentPage.db #making a virtualPage with a shared db with the currentPage
        else:
            self.application.db.clearCurrentEnv() #new a brand new page
        self.extraFeatures = copy.deepcopy(self.site.extraFeatures)
        self.extraFeatures.update(dictExtract(request_kwargs,'_extrafeature_',pop=True))
        self.base_dbstore = request_kwargs.pop('base_dbstore',None)
        self.temp_dbstore = request_kwargs.pop('temp_dbstore',None)
        if self.temp_dbstore is False:
            self.temp_dbstore = self.application.db.rootstore
        dbstore = self.temp_dbstore or self.base_dbstore
        self.dbstore = dbstore if dbstore != self.application.db.rootstore else None
        self.aux_instance =  request_kwargs.pop('_aux_instance',None) or None
        self.user_agent = request.user_agent.string or []
        self._environ = environ
        self._event_subscribers = {}
        self.forked = False # maybe redefine as _forked
        self.filepath = filepath
        self.packageId = packageId
        self.pluginId = pluginId
        self.basename = basename
        self.siteFolder = self.site.site_path
        self.folders = self._get_folders()
        self.called_url = request.url
        self.path_url = request.url_root
        self.request = GnrWebRequest(request)
        self.user_ip = self.request.remote_addr or '0.0.0.0'
        self.response = GnrWebResponse(response)
        self._request = self.request._request
        self._response = self.response._response
        self.response.add_header('Pragma', 'no-cache')
        if self.site.config['x_frame_options']:
            self.response.add_header('X-Frame-Options', self.site.config['x_frame_options'])
        self._htmlHeaders = []
        self._pendingContext = []
        self.local_datachanges = []
        self.pagepath = self.filepath.replace(self.folders['pages'], '')
        self.debug_mode = False
        self._dbconnection = None
        self._user_login = request_kwargs.pop('_user_login', None)
        self.page_timeout = self.site.config.getItem('page_timeout') or PAGE_TIMEOUT
        self.page_refresh = self.site.config.getItem('page_refresh') or PAGE_REFRESH
        self.private_kwargs = dict([(k[:2], v)for k, v in list(request_kwargs.items()) if k.startswith('__')])
        self.pagetemplate = request_kwargs.pop('pagetemplate', None) or getattr(self, 'pagetemplate', None) or \
                            self.site.config['dojo?pagetemplate'] or 'standard.tpl'
        self.css_theme = request_kwargs.pop('css_theme', None) or getattr(self, 'css_theme', None) \
                        or self.site.config['gui?css_theme']
        self.css_theme_variant = request_kwargs.pop('css_theme_variant', None) or getattr(self, 'css_theme_variant', None) \
                        or self.site.config['gui?css_theme_variant'] or 'base'
        self.css_icons = request_kwargs.pop('css_icons', None) or getattr(self, 'css_icons', None)\
                        or self.site.config['gui?css_icons'] or 'retina/gray'
        self.dojo_theme = request_kwargs.pop('dojo_theme', None) or getattr(self, 'dojo_theme', None)
        self.dojo_version = request_kwargs.pop('dojo_version', None) or getattr(self, 'dojo_version', None)
        self.envelope_js_requires= {}
        self.envelope_css_requires= {}
        self._avoid_module_cache = _avoid_module_cache
        self.debug_sql = boolean(request_kwargs.pop('debug_sql', None))
        debug_py = request_kwargs.pop('debug_py', None)
        self.debug_py = False if boolean(debug_py) is not True else debug_py
        #self.polling_enabled = boolean(request_kwargs.pop('polling_enabled')) if 'polling_enabled' in request_kwargs else getattr(self, 'polling_enabled', True)
        self.callcounter = request_kwargs.pop('callcounter', None) or 'begin'
        if not hasattr(self, 'dojo_source'):
            self.dojo_source = self.site.config['dojo?source']
        if 'dojo_source' in request_kwargs:
            self.dojo_source = request_kwargs.pop('dojo_source')
        self.connection = GnrWebConnection(self,
                                           connection_id=request_kwargs.pop('_connection_id', None),
                                           user=request_kwargs.pop('_user', None))
        page_id = request_kwargs.pop('page_id', None)
        self.subdomain = request_kwargs.pop('_subdomain',None) if page_id else request_kwargs.get('_subdomain')        
        self.root_page_id = None
        self.parent_page_id = None
        self.sourcepage_id = request_kwargs.pop('sourcepage_id', None)
        self.instantiateProxies()
        self.onPreIniting(request_args, request_kwargs)
        self._call_handler = self.get_call_handler(request_args, request_kwargs)
        
        self.onIniting(request_args, request_kwargs)
        self._call_args = request_args or tuple()
        self._call_kwargs = dict(request_kwargs)
        if getattr(self,'skip_connection', False) or self._call_kwargs.get('method') == 'onClosePage':
            self.page_item = dict(data=dict())
            self._workdate = datetime.date.today()
            self.page_id = page_id
            self.isMobile = False
            self.deviceScreenSize = None
            self._inited = True
            return
        if page_id:
            self.page_item = self._check_page_id(page_id, kwargs=request_kwargs)
            self._workdate = self.page_item['data']['rootenv.workdate'] #or datetime.date.today()
            self._language = self.page_item['data']['rootenv.language']
        elif self._call_handler_type in ('pageCall', 'externalCall'):
            raise self.site.client_exception('The request must reference a page_id', self._environ)
        else:
            init_info = dict(request_kwargs=request_kwargs, request_args=request_args,
                          filepath=filepath, packageId=packageId, pluginId=pluginId,  basename=basename)
            self.page_item = self._register_new_page(kwargs=request_kwargs,class_info=class_info,init_info=init_info)
        self.isMobile = (self.connection.user_device.startswith('mobile')) or self.page_item['data']['pageArgs'].get('is_mobile')
        self.deviceScreenSize = self.connection.user_device.split(':')[1]
        self._inited = True
        
    def onPageRegistered(self,**kwargs):
        pass

    def _T(self,value,lockey=None):
        return GnrLocString(value,lockey=lockey)
            
    def onPreIniting(self, *request_args, **request_kwargs):
        """TODO"""
        pass

    @property
    def pagename(self):
        return os.path.splitext(os.path.basename(self.filepath))[0].split(os.path.sep)[-1]
    

    @property
    def call_args(self):
        """TODO"""
        return self._call_args
        
    def getCallArgs(self,*args):
        """TODO"""
        if not args:
            return self._call_args
        result = dict()           
        lenargs = len(self._call_args) 
        for i,arg in enumerate(args):
            result[arg] = self._call_args[i] if i<lenargs else None
        return result 
        
    def instantiateProxies(self):
        """TODO"""
        proxy_classes = [(p[:-11],getattr(self,p, None)) for p in dir(self) if p.endswith('_proxyclass')]
        for proxy_name,proxy_class in proxy_classes:
            if proxy_class:
                setattr(self,proxy_name,proxy_class(self))
                
    def _check_page_id(self, page_id=None, kwargs=None):
        if not self.connection.connection_id:
            raise self.site.client_exception('The connection is not longer valid', self._environ)
        if not self.connection.validate_page_id(page_id):
            if self.isGuest:
                return self._register_new_page(page_id=page_id,kwargs=kwargs)
            raise self.site.client_exception('The referenced page_id is not valid in this connection',
                                             self._environ)
        page_item = self.site.register.page(page_id,include_data='lazy')
        if not page_item:
            raise self.site.client_exception('The referenced page_id is cannot be found in site register',
                                             self._environ)
        self.page_id = page_id
        self.root_page_id = page_item['data'].getItem('root_page_id')
        self.parent_page_id = page_item['data'].getItem('parent_page_id')
        return page_item            

    def _register_new_page(self,page_id=None,kwargs=None,class_info=None,init_info=None):
        if not self.connection.connection_id:
            self.connection.electron_static = self._call_kwargs.get('_electron_static')
            self.connection.create()
            
        self.page_id = page_id or getUuid()
        page_info = dict([(k,getattr(self,k,None)) for k in ATTRIBUTES_SIMPLEWEBPAGE])
        data = Bag()   
        data['pageArgs'] = kwargs
        data['class_info'] = class_info
        data['init_info'] = init_info
        data['page_info'] = page_info
        page_item = self.site.register.new_page(self.page_id, self, data=data)
        if self.wsk_enabled and not getattr(self,'system_page',False):
            self.registerToAsyncServer(page_id=self.page_id,page_info=page_info,
                class_info=class_info,init_info=init_info,mixin_set=[])
        self.onPageRegistered(**kwargs)
        return page_item

    def registerToAsyncServer(self,**kwargs):
        self.wsk.sendCommandToPage('','registerNewPage',Bag(kwargs))

    def get_call_handler(self, request_args, request_kwargs):
        """TODO
        
        :param request_args: TODO
        :param request_kwargs: TODO"""
        if '_plugin' in request_kwargs:
            self._call_handler_type = 'plugin'
            return self.pluginhandler.get_plugin(request_kwargs['_plugin'], request_args=request_args,
                                                 request_kwargs=request_kwargs)
        elif 'rpc' in request_kwargs:
            self._call_handler_type = 'externalCall'
            self.skip_connection  = True
            return self.getPublicMethod('rpc', request_kwargs.pop('rpc'))
        elif 'method' in request_kwargs:
            self._call_handler_type = 'pageCall'
            return self._rpcDispatcher
        else:
            self._call_handler_type = 'root'
            return self.rootPage
            
        ###### BEGIN: PROXY DEFINITION ########
        
    def _get_frontend(self):
        if not hasattr(self, '_frontend'):
            if not hasattr(self, 'page_frontend') and hasattr(self, 'dojo_version'):
                self.page_frontend = 'dojo_%s' % self.dojo_version
            frontend_module = gnrImport('gnr.web.gnrwebpage_proxy.frontend.%s' % self.page_frontend)
            frontend_class = getattr(frontend_module, 'GnrWebFrontend')
            self._frontend = frontend_class(self)
        return self._frontend
        
    frontend = property(_get_frontend)
            
    @property 
    def wsk(self):
        if hasattr(self,'asyncServer'):
            return self.asyncServer.wsk
        return self.site.wsk
    
    @property
    def wsk_enabled(self):
        if not hasattr(self, '_wsk_enabled'):
            self._wsk_enabled = self.wsk and self.getPreference('experimental.wsk_enabled',pkg='sys')
        return self._wsk_enabled
    
    @property 
    def dev(self):
        if not hasattr(self, '_dev'):
            self._dev = GnrWebDeveloper(self)
        return self._dev
        
    @property 
    def pdb(self):
        if not hasattr(self, '_pdb'):
            self._pdb = GnrPdbClient(self)
        return self._pdb

    @property
    def utils(self):
        if not hasattr(self, '_utils'):
            self._utils = GnrWebUtils(self)
        return self._utils
        
    @property
    def rpc(self):
        if not hasattr(self, '_rpc'):
            self._rpc = GnrWebRpc(self)
        return self._rpc
        
    @property
    def pluginhandler(self):
        if not hasattr(self, '_pluginhandler'):
            self._pluginhandler = GnrWebPluginHandler(self)
        return self._pluginhandler
    
    @property       
    def jstools(self):
        if not hasattr(self, '_jstools'):
            self._jstools = GnrWebJSTools(self)
        return self._jstools
        
    @property
    def rootenv(self):
        if not hasattr(self,'_rootenv'):
            self._rootenv = self.pageStore().getItem('rootenv')
        return self._rootenv
    
    @public_method
    def dbCurrentEnv(self):
        return Bag(self.db.currentEnv)

    @property
    def mainpackage(self):
        maintable = getattr(self,'maintable',None)
        if not maintable:
            return self.package.name
        return maintable.split('.')[0]

    @property
    def modulePath(self):
        return  '%s.py' %os.path.splitext(sys.modules[self.__module__].__file__)[0]

     
        
    @property 
    def db(self):
        if not getattr(self, '_db',None):
            self._db = self.application.db
            self._db.clearCurrentEnv()
            expirebag = self.globalStore().getItem('tables_user_conf_expire_ts')
            self._db.updateEnv(storename=self.dbstore, workdate=self.workdate, locale=self.locale,
                                maxdate=datetime.date.max,mindate=datetime.date.min,
                               user=self.user, userTags=self.userTags, pagename=self.pagename,
                               mainpackage=self.mainpackage,_user_conf_expirebag=expirebag,
                               external_host=self.external_host)
            
            self._db.setLocale()
            avatar = self.avatar
            if avatar:
                self._db.updateEnv(_excludeNoneValues=True,**self.avatar.extra_kwargs)
            storeDbEnv = self.site.register.get_dbenv(self.page_id,register_name='page') if self.page_id else dict()
            storeDbEnv.pop('workdate',None) #it does not override page workdate
            if len(storeDbEnv)>0:
                self._db.updateEnv(**storeDbEnv.asDict(ascii=True))
            envPageArgs = dictExtract(self.pageArgs,'env_')
            if envPageArgs:
                self._db.updateEnv(**envPageArgs)
            envCallArgs = dictExtract(self._call_kwargs,'dbenv_')
            if envCallArgs:
                self._db.updateEnv(**envCallArgs)
            for dbenv in [getattr(self, x) for x in dir(self) if x.startswith('dbenv_')]:
                kwargs = dbenv() or {}
                self._db.updateEnv(**kwargs)
        return self._db    
    

        
    def _get_workdate(self):
        today = datetime.date.today()
        workdate = getattr(self,'_workdate',None)
        custom_workdate = getattr(self,'_custom_workdate',None)
        if workdate is None or (workdate!=today and not custom_workdate):
            #if workdate != today check if is custom workdate
            with self.pageStore() as store:
                rootenv = store.getItem('rootenv')
                if not rootenv:
                    self._workdate =  today
                    return self._workdate
                workdate = rootenv['workdate']
                custom_workdate = rootenv['custom_workdate']
                if not custom_workdate:
                    workdate = datetime.date.today()
                    rootenv['workdate'] = workdate
                else:
                    self._custom_workdate = custom_workdate
                self._workdate =  workdate
                self._rootenv = rootenv
        return workdate

    def _set_workdate(self, workdate):
        self.pageStore().setItem('rootenv.workdate', workdate)
        self._workdate = workdate
        self.db.workdate = workdate
    workdate = property(_get_workdate, _set_workdate)

    def _get_language(self):
        if not getattr(self,'_language',None):
            self._language = self.pageStore().getItem('rootenv.language') or self.locale.split('-')[0].upper()
        return self._language

    def _set_language(self, language):
        self.pageStore().setItem('rootenv.language', language)
        self._language = language
    language = property(_get_language, _set_language)

    def _set_locale(self, val):
        self._locale = val
        
    def _get_locale(self):
        if not getattr(self,'_locale',None):
            headers_locale = self.request.headers.get('Accept-Language', 'en').split(',')[0]
            self._locale = (self.avatar.locale if self.avatar and getattr(self.avatar,'locale',None) else headers_locale) or 'en' #to check
            #self._locale = headers_locale or 'en'
        return self._locale
    locale = property(_get_locale, _set_locale)
    
    @property
    def workdate_timestamp(self):
        now = datetime.datetime.now()
        return datetime.datetime(self.workdate.year, self.workdate.month, self.workdate.day, now.hour, now.minute, now.second)


    @public_method
    def setWorkdate(self,workdate=None):
        """Set the :ref:`workdate` and return it
        
        ``setWorkdate()`` method is decorated with the :meth:`public_method <gnr.core.gnrdecorator.public_method>` decorator
        
        :param workdate: the :ref:`workdate`"""
        if workdate:
            self.workdate = workdate
        return self.workdate
            
    ###### END: PROXY DEFINITION #########
        
    def __call__(self):
        """Internal method dispatcher"""
        self.pdb.onPageStart()    
        self.onInit() ### kept for compatibility
        self._onBegin()
        args = self._call_args
        kwargs = self._call_kwargs
        result = self._call_handler(*args, **kwargs) 
        
        if hasattr(self,'mixin_set'):
            with self.pageStore() as store:
                store_mixin_set = store.get('mixin_set') or set()
                store.setItem('mixin_set', store_mixin_set.union(self.mixin_set))
        self._onEnd()
        if getattr(self,'_closed',False):
            self.site.register.drop_page(self.page_id, cascade=False)
        return result
    

    def _rpcDispatcher(self, *args, **kwargs):
        method = kwargs.pop('method',None)
        mode = kwargs.pop('mode','bag')
        _serverstore_changes = kwargs.pop('_serverstore_changes',None)
        kwargs.pop('aux_instance',None)
        self._lastUserEventTs = kwargs.pop('_lastUserEventTs', None)
        self._lastRpc = kwargs.pop('_lastRpc', None)
        self._pageProfilers = kwargs.pop('_pageProfilers', None)
        if _serverstore_changes:
            self.site.register.set_serverstore_changes(self.page_id, _serverstore_changes)
        auth = AUTH_OK
        if method not in ('doLogin', 'onClosePage'):
            auth = self._checkAuth(method=method, **kwargs)
            #if auth == AUTH_OK:
            #    auth = self._checkRootPage()
        try:
            self.db #init db property with env
            result = self.rpc(method=method, _auth=auth, **kwargs)
        except GnrSilentException as e:
            self.rpc.error = 'gnrsilent'
            result = Bag(topic=e.topic,parameters=e.parameters)
        except GnrException as e:
            if self.site.debug and (self.isDeveloper() or self.site.force_debug):
                raise
            self.rpc.error = 'gnrexception'
            result = str(e)
        except Exception as e:
            if self.site.debug and (self.isDeveloper() or self.site.force_debug):
                raise
            else:
                exception_record = self.site.writeException(exception=e, traceback=tracebackBag())
                if self.site.error_smtp_kwargs:
                    import sys
                    from weberror.errormiddleware import handle_exception
                    error_handler_kwargs = self.site.error_smtp_kwargs
                    error_handler_kwargs['debug_mode'] = True
                    error_handler_kwargs['simple_html_error'] = False
                    handle_exception(sys.exc_info(), self._environ['wsgi.errors'], **error_handler_kwargs)
                self.rpc.error = 'server_exception'
                result = '<div>%s</div>' %str(e)
                if exception_record:
                    result = '%s <br/> Check Exception Id: %s' %(result,exception_record['id'])
        result_handler = getattr(self.rpc, 'result_%s' % mode.lower())
        return_result = result_handler(result)
        return return_result
        
    def _checkAuth(self, method=None, **parameters):
        pageTags = self.pageAuthTags(method=method, **parameters)
        if not pageTags:
            return AUTH_OK
        if not self.connection.loggedUser:
            if method != 'main':
                return AUTH_EXPIRED
            return AUTH_NOT_LOGGED
        if not self.application.checkResourcePermission(pageTags, self.userTags):
            return AUTH_FORBIDDEN
        return AUTH_OK
    
    def _checkRootPage(self):
        if self.pageOptions.get('standAlonePage') \
            or self.root_page_id or not self.avatar \
                or not self.avatar.avatar_rootpage:
            return AUTH_OK
        result =  AUTH_FORBIDDEN if self.avatar.avatar_rootpage != self.request.path_info else AUTH_OK
        return result
        
    def pageAuthTags(self,method=None,**kwargs):
        return getattr(self,'auth_%s' %method,self.defaultAuthTags if method=='main' else None)
        
    @property
    def defaultAuthTags(self):
        return self.package.attributes.get('auth_default','')

    def mangledHook(self,method,mangler=None,asDict=False,dflt=None,defaultCb=None):
        if asDict:
            prefix='%s_%s_'% (mangler,method)
            return dict([(fname,getattr(self,fname)) for fname in dir(self) 
                                     if fname.startswith(prefix) and fname != prefix and not fname.endswith('_')])    

        def emptyCb(*args,**kwargs):
            return dflt
        handler = getattr(self,'%s_%s' %(mangler.replace('.','_'),method),None)
        if handler is None and defaultCb is False:
            return None
        return handler or defaultCb or emptyCb
    
    @public_method
    def saveHelperValue(self,table=None,name=None,helpcode=None,value=None,customizationPackage=None):
        relpath = f'helper/{name}.xml'
        if table:
            path = self.packageResourcePath(table,relpath,
                                    forcedPackage=customizationPackage)
        else:
            path = self.getResource(relpath,pkg=customizationPackage or self.package)
        data = Bag(path) if os.path.exists(path) else Bag()
        data.setAttr(helpcode,{self.language:value})
        data.toXml(path)
    
    @public_method
    def getHelperData(self,table=None,name=None,**kwargs):
        path = []
        if table:
            path.append(table)
            name = name or 'default'
        if name:
            path.append(name)
        if not hasattr(self,'_helpers'):
            self._helpers = {}
        path = '.'.join(path)
        if path in self._helpers:
            return self._helpers[path],{'path':path,'in_cache':True}
        relpath = f'helper/{name}.xml'
        def bagFromFile(filepath):
            return Bag(filepath) if os.path.exists(filepath) else Bag()
        if table:
            data = bagFromFile(self.packageResourcePath(table,relpath))
            customData = bagFromFile(self.packageResourcePath(table,relpath,
                                    forcedPackage=self.package.name))
            for n in customData:
                d = dict(n.attr)
                d['_custom_package'] = self.package.name
                data.setAttr(n.label,d,_updattr=False)
        else:
            data = bagFromFile(self.getResource(relpath,pkg=self.package))
        self._helpers[path] = data
        return self._helpers[path],{'path':path,'in_cache':False}


    def mixinTableResource(self, table, path,**kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param path: the table resource path"""
        pkg,table = table.split('.')
        result = self.mixinComponent('tables/%s/%s' %(table,path),**kwargs)
        self.mixinComponent('tables/_packages/%s/%s/%s' %(pkg,table,path),safeMode=True,**kwargs)
        return result

        
    def mixinComponent(self, *path,**kwargs):
        """TODO
        
        :param pkg: the :ref:`package <packages>` object"""
        safeMode = kwargs.pop('safeMode',None)
        if safeMode:
            try:
                return self.site.resource_loader.mixinPageComponent(self, *path,**kwargs)
            except GnrMixinNotFound:
                pass
        else:
            return self.site.resource_loader.mixinPageComponent(self, *path,**kwargs)


    def zoomLink(self,table=None,pkey=None,formResource=None,caption=None,zoomMode=None,zoomUrl=None,title=None):
        zoomMode = zoomMode or 'palette'
        zoomUrl = zoomUrl or ''
        title = title or ''
        jsmethod = "genro.dlg.makeZoomElement({table:'%s',formResource:'%s',pkey:'%s',evt:event,main_call:'main_form',palette_dockTo:false,mode:'%s',zoomUrl:'%s',title:'%s'})" %(table,formResource,pkey,zoomMode,zoomUrl,title)
        return '<a href="#" onclick="%s" class="tablePaletteZoomLink" >%s</a>' %(jsmethod,caption)
    
    
    @public_method
    def tableTemplate(self, table=None, tplname=None, asSource=False):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param tplname: the template name
        :param ext: TODO
        :param asSource: boolean. TODO"""
        result,attr = self.templateFromResource(table=table,tplname=tplname)
        if asSource:
            return result,attr
        if 'html' in attr:
            return result['content']
        return result['compiled']

    @public_method
    def templateFromResource(self, table=None, tplname=None):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param tplname: the template name
        :param ext: TODO
        :param asSource: boolean. TODO"""
        if table:
            result,path = self.getTableResourceContent(table=table,path='tpl/%s' %tplname,ext=['xml','html'])
        else:
            result,path = self._getResourceContent(resource=tplname,pkg=self.package.name,ext=['xml','html'])
        if not path:
            return '',{'respath':''}
        r_path,r_ext = os.path.splitext(path)
        if r_ext=='.html':
            result = Bag(content=result)
            path = '%s.xml' %r_path
            return result,{'respath':path,'html':True}
        else:
            result=Bag(result)
            return result,{'respath':path}

    @public_method
    def renderTemplate(self,table=None,record_id=None,letterhead_id=None,tplname=None,missingMessage=None,template=None,record=None,**kwargs):
        from gnr.web.gnrbaseclasses import TableTemplateToHtml
        htmlbuilder = TableTemplateToHtml(table=self.db.table(table))
        return htmlbuilder.contentFromTemplate(record=record or record_id,template=template or self.loadTemplate('%s:%s' %(table,tplname),missingMessage=missingMessage))

    @public_method
    def loadTemplate(self,template_address,asSource=False,missingMessage=None,**kwargs):
        #se template_address non ha : ---> risorsa
        #template_address = 'field:pkey'
        
        missingMessage = missingMessage or '<div class="chunkeditor_emptytemplate">Missing Template</div>'
        dataInfo = dict()
        if ':' in template_address:
            segments,pkey = template_address.split(':')
            if segments:
                segments = segments.split('.')
        else:
            segments = None
            pkey = template_address
        
        if not segments or len(segments)==2:
            table = '.'.join(segments) if segments else None
            data = None
            if self.db.package('adm') and table:
                data,metadata = self.db.table('adm.userobject').loadUserObject(objtype='template',code=pkey,tbl=table)
                if data and metadata['private'] and metadata['userid'] != self.user:
                    data = None
            if not data:
                resource_name = pkey
                data,dataInfo =  self.templateFromResource(table=table,tplname=resource_name)
        else:
            pkg,table,field = segments
            data = Bag(self.db.table('.'.join([pkg,table])).readColumns(pkey=pkey,columns=field))
        if asSource:
            if data:
                mainNode = data.getNode('compiled.main')
                editcols = mainNode.attr.get('editcols') if mainNode else None
                if editcols:
                    for k,v in list(data['varsbag'].items()):
                        if v['editable']:
                            editcols[v['varname']] = self.app.getFieldcellPars(field=v['fieldpath'],table=table).asDict()
                            if v['editable'] is not True and '=' in v['editable']:
                                editcols[v['varname']].update(asDict(v['editable']))
            return data,dataInfo
        return data['compiled'] if data else missingMessage
        
    @public_method
    def saveTemplate(self,template_address,data,inMainResource=False):
        #pkg.table.field:pkey
        #pkg.table:resource_module
        #pkg.table:resource_module,custom
        if ':' in template_address:
            segments,pkey = template_address.split(':')
            if segments:
                segments = segments.split('.')
        else:
            segments = None
            pkey = template_address


        if not segments or len(segments)==2:
            custom = False
            resource_name = pkey
            if segments:
                resource_table = '.'.join(segments)
                filepath='tpl/%s.xml' %resource_name
            else:
                resource_table = None
                filepath = '%s.xml' %resource_name
            if ',' in resource_name:
                resource_name = resource_name.split(',')[0]
                custom = True
            respath = self.packageResourcePath(table=resource_table,filepath=filepath,custom=custom,
                                                forcedPackage=self.package.name if not inMainResource else None)
            data.toXml(respath,autocreate=True)
            return respath
        else:
            pkg,table,field = segments
            tblobj = self.db.table('.'.join([pkg,table]))
            record = tblobj.rec(pkey=pkey,for_update=True).output('record')
            record[field] = data
            tblobj.update(record)
            self.db.commit()

    @property
    def isGuest(self):
        """TODO"""
        return self.user == self.connection.guestname

    def callPackageHooks(self,method,*args,**kwargs):
        result = {}
        for pkgId in list(self.packages.keys()): # custom methodname_packagename
            handlername = '%s_%s' %(method,pkgId)
            if hasattr(self,handlername):
                result[handlername] = getattr(self,handlername)(*args,**kwargs)
        if hasattr(self,method):#main one with method name
            result[method] = getattr(self,method)(*args,**kwargs)
        return result

    def doLogin(self, login=None,guestName=None,authenticate=True, rootenv=None,**kwargs):
        """Service method. Set user's avatar into its connection if:
        
        * The user exists and his password is correct
        * The user is a guest
        
        :param login: TODO
        :param guestName: TODO"""
        
        loginPars = {}
        if guestName:
            avatar = self.application.getAvatar(guestName)
        else:
            avatar = self.application.getAvatar(login['user'], password=login.get('password'),
                                                group_code=login.get('group_code'),
                                                authenticate=authenticate, page=self, **kwargs)
        if avatar:
            self.avatar = avatar
            #self.connection.change_user(user=avatar.user,user_id=avatar.user_id,user_name=avatar.user_name,
            #                            user_tags=avatar.user_tags)
            errdict = self.callPackageHooks('onAuthenticating',avatar,rootenv=rootenv)
            err = [err for err in errdict.values() if err is not None]
            if err:
                login['error'] = ', '.join(err)
                return (login, loginPars)
            self.site.onAuthenticated(avatar)
            self.connection.change_user(avatar)
            self.site.connectionLog('open')
            login['message'] = ''
            loginPars = avatar.loginPars
            loginPars.update(avatar.extra_kwargs)
            try:
                self.btc.cleanUserBatches(self.user)
            except self.site.register.locked_exception:
                pass
        else:
            login['message'] = 'invalid login'
        return (login, loginPars)

    
    def onInit(self):
        """Hook method. TODO"""
        pass
        
    def onIniting(self, request_args, request_kwargs):
        """Callback onIniting called in early stages of page initialization
        
        :param request_args: TODO
        :param request_kwargs: TODO"""
        pass
        
    def onSaving(self, recordCluster, recordClusterAttr, resultAttr=None):
        """TODO
        
        :param recordCluster: TODO
        :param recordClusterAttr: TODO
        :param resultAttr: TODO"""
        pass
        
    def onSaved(self, record, resultAttr=None, **kwargs):
        """TODO
        
        :param record: TODO
        :param resultAttr: TODO"""
        pass
        
    def onLoadingRelatedMethod(self,table,sqlContextName=None):
        return 'onLoading_%s' % table.replace('.', '_')
    
    def onDeleting(self, recordCluster, recordClusterAttr):
        """TODO
        
        :param recordCluster: TODO
        :param recordClusterAttr: TODO"""
        pass
        
    def onDeleted(self, record):
        """TODO
        
        :param record: TODO"""
        pass
        
    def onBegin(self):
        """TODO"""
        pass
        
    def _onBegin(self):
        self.onBegin()
        self._publish_event('onBegin')
        
    def onEnd(self):
        """TODO"""
        pass
        
    def getService(self, service_type=None,service_name=None, **kwargs):
        """TODO
        
        :param service_type: TODO"""
        service_name = service_name or service_type
        return self.site.getService(service_type=service_type,service_name=service_name, **kwargs)
        
    def _onEnd(self):
        self._publish_event('onEnd')
        self.onEnd()
        
    def collectClientDatachanges(self):
        """TODO"""
        self._publish_event('onCollectDatachanges')
        store_datachanges = self.site.register.subscription_storechanges(self.user,self.page_id) or []
        result = Bag()
        local_datachanges = self.local_datachanges or []
        for j, change in enumerate(local_datachanges+store_datachanges):
            result.setItem('sc_%i' % j, change.value, change_path=change.path, change_reason=change.reason,
                           change_fired=change.fired, change_attr=change.attributes,
                           change_ts=change.change_ts, change_delete=change.delete)
        return result

        
    def _subscribe_event(self, event, caller):
        assert hasattr(caller, 'event_%s' % event)
        self._event_subscribers.setdefault(event, []).append(caller)
        
    def _publish_event(self, event):
        for subscriber in self._event_subscribers.get(event, []):
            getattr(subscriber, 'event_%s' % event)()
            
    def rootPage(self,*args, **kwargs):
        """TODO"""
        user_agent = self.request.headers.get('User-Agent', '')
        user_agent = self.user_agent

        if 'MSIE' in user_agent and not 'chromeframe' in user_agent:
            raise GnrUnsupportedBrowserException
        self.charset = 'utf-8'
        arg_dict = self.build_arg_dict(**kwargs)
        tpl = self.pagetemplate
        if not isinstance(tpl, str):
            tpl = '%s.%s' % (self.pagename, 'tpl')
        lookup = TemplateLookup(directories=self.tpldirectories, output_encoding=self.charset,
                                encoding_errors='replace')
        try:
            mytemplate = lookup.get_template(tpl)
        except:
            raise GnrWebPageException("No template %s found in %s" % (tpl, str(self.tpldirectories)))
        self.htmlHeaders()
        return mytemplate.render(mainpage=self, **arg_dict).decode()
        
    def rpc_changeLocale(self, locale):
        """TODO
        
        :param locale: the current locale (e.g: en, en_us, it)"""
        self.connection.locale = locale.lower()
        
    def toText(self, obj, locale=None, format=None, mask=None, encoding=None, dtype=None):
        """TODO
        
        :param obj: TODO
        :param locale: the current locale (e.g: en, en_us, it)
        :param format: TODO
        :param mask: TODO
        :param encoding: the encoding type
        :param dtype: the :ref:`datatype`"""
        locale = locale or self.locale
        return toText(obj, locale=locale, format=format, mask=mask, encoding=encoding)
        

    def clientDatetime(self,ts=None,serverTimeDelta=None):
        serverTimeDelta = serverTimeDelta or self.rootenv['serverTimeDelta']
        ts = ts or datetime.datetime.now()
        if serverTimeDelta:
            return ts-timedelta(milliseconds=serverTimeDelta)
        return ts



    def getUuid(self):
        """TODO"""
        return getUuid()
    
    def getForcedHeaders(self):
        return {}
        
    def addHtmlHeader(self, tag, innerHtml='',attributes=None, **kwargs):
        """TODO
        
        :param tag: TODO
        :param innerHtml: TODO"""
        attributes = attributes or dict()
        attributes.update(kwargs)
        attrString = ' '.join(['%s="%s"' % (k, str(v)) for k, v in list(attributes.items())])
        self._htmlHeaders.append('<%s %s>%s</%s>' % (tag, attrString, innerHtml, tag))
        
    def htmlHeaders(self):
        """TODO"""
        pass
        
    @property
    def pageArgs(self):
        return self.pageStore().getItem('pageArgs') or {}

    @property
    def localizer(self):
        return self.application.localizer

    @public_method
    def getRemoteTranslation(self, txt=None,language=None,**kwargs):
        return self.localizer.getTranslation(txt,language=language or self.locale)

    def localize(self, txt, language=None,**kwargs):
        return self.localizer.translate(txt,language=language or self.locale)
    _ = localize


    def _getProxyObject(self, method, prefix=None):
        proxy_name, submethod = method.split('.', 1)
        if proxy_name=='_package':
            sep='.'
            pkg_name,sep,submethod = submethod.rpartition(sep)
            proxy_object = self.db.package(pkg_name)
        elif proxy_name=='_table':
            sep='.'
            table_name,sep,submethod = submethod.rpartition(sep)
            proxy_object = self.db.table(table_name)
            handler = getattr(proxy_object,submethod)
            permissions = getattr(handler,'permissions',None)
            if not self.checkTablePermission(table=table_name,permissions=permissions):
                raise self.exception('business_logic',message='Operation %s is not allowed' %submethod)
        elif proxy_name == '_tblscript':
            table_pkg,table_name,table_respath,class_name,submethod = submethod.split('.')
            proxy_object = self.loadTableScript(table='.'.join((table_pkg,table_name)),respath=table_respath,class_name=class_name)
        elif proxy_name == '_resourcescript':
            pkg_name,respath,class_name,submethod = submethod.split('.')
            proxy_object = self.loadResourceScript(respath,class_name=class_name,pkg=pkg_name)
        elif proxy_name == '_service':
            l = submethod.split('.')
            if len(l)==2:
                service_type,submethod = l
                proxy_object = self.getService(service_type)
            else:
                service_type,service_name,submethod = l
                proxy_object = self.getService(service_type,service_name)
        else:
            proxy_object = getattr(self, proxy_name, None)
        if not proxy_object:
            proxy_object = self.pluginhandler.get_plugin(proxy_name)
        else:
            if '.' in submethod:
                sl = submethod.split('.')
                submethod = sl.pop()
                while proxy_object and sl:
                    subproxy = sl.pop(0)
                    proxy_object = getattr(proxy_object,subproxy)
        return proxy_object, submethod

    def getPublicMethod(self, prefix, method):
        """TODO
        
        :param prefix: The method prefix. It can be:
                       
                       * 'remote': this prefix is used for the :ref:`dataremote`
                       * 'rpc': this prefix is used for the :ref:`datarpc`
                       
        :param method: TODO"""
        if callable(method):
            return method
        handler = None
        if ';' in method:
            mixin_info, method = method.split(';')
            __mixin_pkg, __mixin_path = mixin_info.split('|')
            if __mixin_pkg=='*':
                __mixin_pkg=None
            __mixin_path_list = __mixin_path.split('/')
            self.mixinComponent(*__mixin_path_list, pkg=__mixin_pkg)
        if '.' in method:
            proxy_object,submethod = self._getProxyObject(method)                 
        else:
            proxy_object = self
            submethod = method
        handler = getattr(proxy_object, submethod, None)
        if not handler or not getattr(handler, 'is_rpc', False):
            handler = getattr(proxy_object, '%s_%s' % (prefix, submethod),None)
        
        if handler and getattr(handler,'signed',None):
            error = self.site.auth_token_generator.verify_url(self.request._request.url)
            if error:
                raise GnrSignedTokenException(error)
            
        if handler and getattr(handler, 'tags',None):
            userTags = self.userTags or self.basicAuthenticationTags()
            if not self.application.checkResourcePermission(handler.tags, userTags):
                raise self.exception(GnrUserNotAllowed,method=method)
        if not handler:
            self.clientPublish('floating_message',message='missing public method %s' %method,messageType='error')
        return handler

    def basicAuthenticationTags(self):
        authorization = self.request.headers.get('Authorization')
        if not authorization:
            raise GnrBasicAuthenticationError('Missing Basic Authorization')
        authmode,login = authorization.split(' ')
        if authmode!='Basic':
            raise GnrBasicAuthenticationError('Wrong Authorization Mode')
        user,pwd = b64decode(login).decode().split(':')
        self.avatar = self.application.getAvatar(user,pwd,authenticate=True)
        if not self.avatar:
            raise GnrBasicAuthenticationError('Wrong Authorization Login')
        return self.avatar.user_tags
        
    def getWsMethod(self, method):
        """TODO
        
        :param prefix: The method prefix. It can be:
                       
                       * 'remote': this prefix is used for the :ref:`dataremote`
                       * 'rpc': this prefix is used for the :ref:`datarpc`
                       
        :param method: TODO"""
        handler = None
        if ';' in method:
            mixin_info, method = method.split(';')
            __mixin_pkg, __mixin_path = mixin_info.split('|')
            if __mixin_pkg=='*':
                __mixin_pkg=None
            __mixin_path_list = __mixin_path.split('/')
            self.mixinComponent(*__mixin_path_list, pkg=__mixin_pkg)
        if '.' in method:
            proxy_object,submethod = self._getProxyObject(method)                 
        else:
            proxy_object = self
            submethod = method
        handler = getattr(proxy_object, submethod, None)
        if handler and getattr(handler, 'tags',None):
            if not self.application.checkResourcePermission(handler.tags, self.userTags):
                raise self.exception(GnrUserNotAllowed,method=method)
        return handler

    def exception(self, exception, **kwargs):
         """TODO

         :param exception: the exception raised.
         :param record: TODO.
         :param msg: TODO."""
         if isinstance(exception, str):
             exception = EXCEPTIONS.get(exception)
             if not exception:
                 raise exception
         return exception(user=self.user,localizer=self.application.localizer,**kwargs)

    def build_arg_dict(self, _nodebug=False, _clocomp=False, **kwargs):
        """TODO
        
        :param _nodebug: no debug mode
        :param _clocomp: enable closure compile
        """
        gnr_static_handler = self.site.storage('gnr')
        gnrModulePath = gnr_static_handler.url(self.gnrjsversion)
        arg_dict = {}
        self.frontend.frontend_arg_dict(arg_dict)
        arg_dict['customHeaders'] = self._htmlHeaders
        arg_dict['charset'] = self.charset
        arg_dict['pageModule'] = self.filepath.replace('\\',r'\\') if self.site.debug else ''
        arg_dict['filename'] = self.pagename
        arg_dict['pageMode'] = 'wsgi_10'
        arg_dict['baseUrl'] = self.site.home_uri
        kwargs['servertime'] = datetime.datetime.now()
        kwargs['websockets_url'] = '/websocket' if self.wsk_enabled else None
        self.getPwaIntegration(arg_dict)
        self.getSquareLogoUrl(arg_dict)
        self.getCoverLogoUrl(arg_dict)
        self.getGoogleFonts(arg_dict)
        self.getSentryJs(arg_dict)
        if self.debug_sql:
            kwargs['debug_sql'] = self.debug_sql
        if self.debug_py:
            kwargs['debug_py'] = self.debug_py

        if self.isDeveloper():
            kwargs['isDeveloper'] = True
        if self.isMobile:
            kwargs['isMobile'] = True
        kwargs['deviceScreenSize'] = self.deviceScreenSize
        kwargs['extraFeatures'] = dict(self.extraFeatures)
        kwargs['isCordova'] = self.connection.is_cordova
        localroot = None
        if self.connection.electron_static:
            localroot ='file://%s/app/lib/static/' %self.connection.electron_static
        if getattr(self,'_avoid_module_cache',None):
            kwargs['_avoid_module_cache'] = True
        safety_re = re.compile(r"(.*<.*.*?>.+?</.*>)")
        startArgs = dict([(k,self.catalog.asTypedText(v)) for k,v in list(kwargs.items())])
        for arg in list(startArgs.keys()):
            if re.search(safety_re, arg):
                startArgs.pop(arg, None)
                continue
            if re.search(safety_re, startArgs[arg]):
                startArgs[arg]= None
        arg_dict['startArgs'] = toJson(startArgs)
        arg_dict['page_id'] = self.page_id or getUuid()
        arg_dict['bodyclasses'] = self.get_bodyclasses()
        arg_dict['gnrModulePath'] = gnrModulePath
        gnrimports = self.frontend.gnrjs_frontend()
        #if _nodebug is False and _clocomp is False and (self.site.debug or self.isDeveloper()):
        if localroot:
            arg_dict['genroJsImport'] = [gnr_static_handler.url(self.gnrjsversion, 'js', '%s.js' % f, _localroot=localroot) for f in gnrimports]
        elif _nodebug is False and _clocomp is False and (self.isDeveloper()):
            arg_dict['genroJsImport'] = [self.mtimeurl(self.gnrjsversion, 'js', '%s.js' % f) for f in gnrimports]
        elif _clocomp or self.site.config['closure_compiler']:
            jsfiles = [gnr_static_handler.internal_path(self.gnrjsversion, 'js', '%s.js' % f) for f in gnrimports]
            arg_dict['genroJsImport'] = [self.jstools.closurecompile(jsfiles)]
        else:
            if not self.site.compressedJsPath or self.site.debug:
                jsfiles = [gnr_static_handler.internal_path(self.gnrjsversion, 'js', '%s.js' % f) for f in gnrimports]
                self.site.compressedJsPath = self.jstools.compress(jsfiles)
            arg_dict['genroJsImport'] = [self.site.compressedJsPath]
        arg_dict['css_genro'] = self.get_css_genro()
        arg_dict['js_requires'] = [x for x in [self.getResourceUri(r, 'js', add_mtime=True) for r in self.js_requires]
                                   if x]
        if self.isMobile:
            arg_dict['js_requires'].append(self.site.getStaticUrl('rsrc:js_libs','hammer.min.js'))
            arg_dict['js_requires'].append(self.site.getStaticUrl('rsrc:js_libs','DragDropTouch.js'))
        css_path, css_media_path = self.get_css_path()
        arg_dict['css_requires'] = css_path
        arg_dict['css_media_requires'] = css_media_path
        
        return arg_dict
    
    def getPwaIntegration(self, arg_dict):
        pwa_config = self.site.pwa_handler.configuration()
        if pwa_config is not None:
            arg_dict['pwa'] = not pwa_config.get('disabled')

    def getSquareLogoUrl(self, arg_dict):
        site_favicon = self.site.config['favicon?name']
        pref_favicon = self.getPreference('gui_customization.owner.square_logo', pkg='adm')
        if not site_favicon and pref_favicon:
            arg_dict['favicon'] = pref_favicon
        elif not pref_favicon and site_favicon:
            arg_dict['favicon'] = self.site.getStaticUrl('site:favicon',site_favicon)
        else:
            arg_dict['favicon'] = self.getResourceUri('app_images/square_logo.svg',add_mtime=self.isDeveloper())
        return arg_dict

    def getCoverLogoUrl(self, arg_dict):
        logo_url = self.getPreference('gui_customization.owner.cover_logo', pkg='adm')
        clientlogo = self.site.storageNode(self.site.site_path,'/img/logo/clientlogo.png').exists
        if logo_url:
            arg_dict['logo_url'] = logo_url
        elif clientlogo:
            arg_dict['logo_url'] = '/_site/img/logo/clientlogo.png'
        else:
            arg_dict['logo_url'] = self.getResourceUri('app_images/cover_logo.svg',add_mtime=self.isDeveloper())
        return arg_dict

    def getGoogleFonts(self, arg_dict):
        google_fonts = getattr(self,'google_fonts',None)
        if google_fonts:
            arg_dict['google_fonts'] = google_fonts
        return arg_dict

    def getSentryJs(self, arg_dict):
        if self.site.config['sentry?js']:
            arg_dict['sentryjs'] = self.site.config['sentry?js']
            for ck in ['sample_rate', 'traces_sample_rate', 'profiles_sample_rate',
                       'replays_session_sample_rate', 'replays_on_error_sample_rate']:
                cv = self.site.config.get(f"sentry?{ck}")
                if cv is None:
                    cv = "0.0"
                arg_dict[f'sentry_{ck}'] = cv
        return arg_dict


    def mtimeurl(self, *args):
        """TODO"""
        gnr_static_handler = self.site.storage('gnr')
        url = gnr_static_handler.url(*args)
        mtime = gnr_static_handler.mtime(*args)
        url = '%s?mtime=%0.0f' % (url, mtime)
        return url
        
    def homeUrl(self):
        """TODO"""
        return self.site.home_uri
        
    def packageUrl(self, *args, **kwargs):
        """TODO"""
        pkg = kwargs.get('pkg', self.packageId)
        return self.site.pkg_page_url(pkg, *args)

    def getUserTableConfig(self,table=None,**kwargs):
        if not self.avatar or self.pageOptions.get('userConfig') is False:
            return Bag()
        return self.db.table(table).getUserConfiguration(user=self.user,user_group=self.avatar.group_code)
        

    def checkTablePermission(self,table=None,permissions=None):
        if not permissions:
            return True
        permissions = set(permissions.split(',') if isinstance(permissions, str) else permissions)
        availablePermissions = set(self.db.table(table).availablePermissions.split(',')).union(set(['hidden','readonly']))
        if not permissions.issubset(availablePermissions):
            raise self.exception('generic',description='Permissions %s are not defined in table %s' %(','.join(permissions.difference(availablePermissions)),table))
        tableconf = self.getUserTableConfig(table=table)
        tbl_forbidden = tableconf['tbl_forbidden']
        tbl_permission = tableconf['tbl_permission']
        checkset = set()
        if tbl_forbidden:
            checkset = checkset.union(tbl_forbidden.split(','))
        if tbl_permission:
            checkset = checkset.union(tbl_permission.split(','))
        
        forbidden = checkset.intersection(permissions)
        return not forbidden

    def getDomainUrl(self, path='', **kwargs):
        """TODO
        
        :param path: TODO"""
        params = urllib.parse.urlencode(kwargs)
        path = '%s/%s' % (self.site.home_uri.rstrip('/'), path.lstrip('/'))
        if params:
            path = '%s?%s' % (path, params)
        return path

    @property
    def external_host(self):
        external_host = self.request.host_url if hasattr(self, 'request') else self.site.configurationItem('wsgi?external_host',mandatory=True) 
        return external_host

    def externalUrl(self, path, **kwargs):
        """TODO
        
        :param path: TODO"""
        return self.site.externalUrl(path, **kwargs)

    def externalUrlToken(self, path, _expiry=None, _host=None,method='root',max_usages=None,allowed_user=None,assigned_user_id=None,**kwargs):
        """TODO
        
        :param path: TODO
        :param method: TODO
        """
        assert 'sys' in self.site.gnrapp.packages
        external_token = self.db.table('sys.external_token').create_token(path, expiry=_expiry, allowed_host=_host,assigned_user_id=assigned_user_id,
                                                                          method=method, parameters=kwargs,max_usages=max_usages,
                                                                          allowed_user=allowed_user,exec_user=self.user)
        return self.externalUrl(path, gnrtoken=external_token)
        

    
    @property
    def device_mode(self):
        if self.isMobile:
            return 'mobile'
        return self.getUserPreference('theme.device_mode',pkg='sys') or 'std'

    def get_bodyclasses(self):   #  is still necessary _common_d11?
        """TODO"""
        theme_variant = self.getPreference('theme.theme_variant',pkg='sys') or ''
        if theme_variant:
            theme_variant = 'theme_variant_%s' %theme_variant
        theme_variant = '%s mode_%s' %(theme_variant,self.device_mode)
        return '%s %s %s _common_d11 pkg_%s page_%s %s ' % ((self.site.config['gui?css_theme'] or ''),
        self.frontend.theme or '',theme_variant, self.packageId, self.pagename, getattr(self, 'bodyclasses', ''))
        
    def get_css_genro(self):
        """TODO"""
        css_genro = self.frontend.css_genro_frontend()
        for media in list(css_genro.keys()):
            css_genro[media] = [self.mtimeurl(self.gnrjsversion, 'css', '%s.css' % f) for f in css_genro[media]]
        return css_genro
        
    def _get_domSrcFactory(self):
        return self.frontend.domSrcFactory
        
    domSrcFactory = property(_get_domSrcFactory)
        
    def newSourceRoot(self,rootAttributes=None):
        """TODO"""
        return self.domSrcFactory.makeRoot(self,rootAttributes=rootAttributes)
        
    def newGridStruct(self, maintable=None):
        """It creates a :class:`GnrGridStruct <gnr.web.gnrwebstruct.GnrGridStruct>` class that
        handles a :ref:`struct` for a :ref:`grid` and return it
        
        :param maintable: the :ref:`database table <table>` to which the struct refers to.
                          For more information, check the :ref:`maintable` section"""
        return GnrGridStruct.makeRoot(self, maintable=maintable)
        
    def _get_folders(self):
        return {'pages': self.site.pages_dir,
                'site': self.site.site_path,
                'current': os.path.dirname(self.filepath)}


    def subscribeTable(self, table, subscribe=True,subscribeMode=None):
        """TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param subscribe: boolean. TODO"""
        self.site.register.subscribeTable(page_id=self.page_id,table=table,subscribe=subscribe,subscribeMode=subscribeMode)            
                    
    def pageStore(self, page_id=None, triggered=True):
        """TODO
        
        :param page_id: the id of the page
        :param triggered: boolean. TODO"""
        page_id = page_id or self.sourcepage_id or self.page_id
        return self.site.register.pageStore(page_id, triggered=triggered)

    def globalStore(self,triggered=True):
        return self.site.register.globalStore(triggered=triggered)
        
    def connectionStore(self, connection_id=None, triggered=True):
        """TODO
        
        :param connection_id: TODO
        :param triggered: boolean. TODO"""
        connection_id = connection_id or self.connection_id
        return self.site.register.connectionStore(connection_id, triggered=triggered)
        
    def userStore(self, user=None, triggered=True):
        """TODO
        
        :param user: the username
        :param triggered: boolean. TODO"""
        user = user or self.user
        return self.site.register.userStore(user, triggered=triggered)
        
    @public_method
    def setStoreSubscription(self, storename=None, client_path=None, active=True):
        """TODO
        
        :param storename: TODO
        :param client_path: TODO
        :param active: boolean. TODO"""
        self.site.register.setStoreSubscription(page_id=self.page_id,storename=storename, client_path=client_path, active=active)
        
    def _get_pkgapp(self):
        if not hasattr(self, '_pkgapp'):
            self._pkgapp = self.site.gnrapp.packages[self.packageId]
        return self._pkgapp
        
    pkgapp = property(_get_pkgapp)
        
    def _get_sitepath(self):
        return self.site.site_path
        
    sitepath = property(_get_sitepath)
        
    def _get_siteUri(self):
        return self.site.home_uri
        
    siteUri = property(_get_siteUri)
        
    def _get_parentdirpath(self):
        try:
            return self._parentdirpath
        except AttributeError:
            self._parentdirpath = self.resolvePath()
            return self._parentdirpath
            
    parentdirpath = property(_get_parentdirpath)
        
    @property
    def application(self):
        """TODO"""
        return self.site.gnrapp
        
    @property
    def app(self):
        """TODO"""
        if not hasattr(self, '_app'):
            self._app = GnrWebAppHandler(self)
        return self._app
        
    @property
    def menu(self):
        """TODO"""
        if not hasattr(self, '_menu'):
            self._menu = GnrMenuProxy(self)
        return self._menu

    @property
    def btc(self):
        """TODO"""
        if not hasattr(self, '_btc'):
            self._btc = GnrWebBatch(self)
        return self._btc
        
    @property
    def catalog(self):
        """TODO"""
        return self.application.catalog
        
    @property
    def userTags(self):
        """TODO"""
        if not self.avatar:
            return ''
        
        tags = self.avatar.user_tags
        user_local_tags = self.userLocalTags
        if user_local_tags:
            tags = tags.split(',')
            for t in user_local_tags.split(','):
                if not t in tags:
                    tags.append(t)
            tags = ','.join(tags)
        return tags
    
    @property
    def userLocalTags(self):
        if not hasattr(self,'_rootenv'):
             return
        return self.rootenv['user_local_tags']
    
    @property
    def userMenu(self):
        if self.avatar.menubag:
            return self.avatar.menubag['root']
        
    def _get_user(self):
        if not getattr(self,'_user',None):
            self._user = self.connection.user
        return self._user

    def _set_user(self,user):
        self._user = user

    user = property(_get_user, _set_user)

    def _get_connection_id(self):
        if not getattr(self,'_connection_id',None):
            self._connection_id = self.connection.connection_id
        return self._connection_id

    def _set_connection_id(self,connection_id):
        self._connection_id = connection_id

    connection_id = property(_get_connection_id, _set_connection_id)

        
    def _set_avatar(self, avatar):
        self._avatar = avatar
        
    def _get_avatar(self):
        if not hasattr(self, '_avatar'):
            if self.isGuest or getattr(self, 'skip_connection', False):
                return
            connection = self.connection
            avatar_extra = connection.avatar_extra or dict()
            self._avatar = self.application.getAvatar(self.user, tags=connection.user_tags, page=self,
                                                      **avatar_extra)
        return self._avatar


    avatar = property(_get_avatar, _set_avatar)

    def _get_siteName(self):
        if not getattr(self,'_siteName',None):
            if os.path.exists(os.path.join(self.siteFolder,'siteconfig.xml')):
                #legacymode
                self._siteName = os.path.basename(self.siteFolder.rstrip('/'))
            else:
                self._siteName = os.path.basename(os.path.dirname(self.siteFolder))
        return self._siteName

    def _set_siteName(self,siteName):
        self._siteName = siteName

    siteName = property(_get_siteName, _set_siteName)

    def checkPermission(self, pagepath, relative=True):
        """TODO
        
        :param pagepath: TODO
        :param relative: TODO"""
        return self.application.checkResourcePermission(self.auth_tags, self.userTags)
        
    def get_css_theme(self):
        """Get the css_theme and return it. The css_theme get is the one defined the :ref:`siteconfig_gui`
        tag of your :ref:`sites_siteconfig` or in a single :ref:`webpage` through the
        :ref:`webpages_css_theme` webpage variable"""
        return self.css_theme

        
    def get_css_theme_variant(self):
        """Get the css_theme and return it. The css_theme get is the one defined the :ref:`siteconfig_gui`
        tag of your :ref:`sites_siteconfig` or in a single :ref:`webpage` through the
        :ref:`webpages_css_theme` webpage variable"""
        return self.css_theme_variant

    def get_css_icons(self):
        """Get the css_icons and return it. The css_icons get is the one defined the :ref:`siteconfig_gui`
        tag of your :ref:`sites_siteconfig` or in a single :ref:`webpage` through the
        :ref:`webpages_css_icons` webpage variable"""
        return self.css_icons
            
    def get_css_path(self, requires=None):
        """Get the path of the css resources, that are:
        
        * the :ref:`css_icons <css_icons>`
        * the :ref:`css_requires`
        * the :ref:`css_theme <css_themes>`
        
        :param requires: TODO If None, get the css_requires string included in a :ref:`webpage`"""
        requires = [r for r in (requires or self.css_requires) if r]
        css_theme = self.get_css_theme() or 'ludo'
        css_icons = self.get_css_icons()
        css_theme_variant =  self.get_css_theme_variant()
        if css_theme:
            requires.append('themes/%s' %css_theme)
        requires.append('themes/{css_theme}/{css_theme_variant}'.format(css_theme=css_theme,css_theme_variant=css_theme_variant))
        if self.dbstore:
            requires.append('multidb_{dbstore}/theme_variant'.format(dbstore=self.dbstore))
        if css_icons:
            requires.append('css_icons/%s/icons' %css_icons)
        self.onServingCss(requires)
        #requires.reverse()
        filepath = os.path.splitext(self.filepath)[0]
        css_requires = []
        css_media_requires = {}
        for css in requires:
            if ':' in css:
                css, media = css.split(':')
            else:
                media = None
            csslist = self.site.resource_loader.getResourceList(self.resourceDirs, css, 'css')
            if csslist:
                #csslist.reverse()
                css_uri_list = [self.getResourceUri(css, add_mtime=True) for css in csslist]
                if media:
                    css_media_requires.setdefault(media, []).extend(css_uri_list)
                else:
                    css_requires.extend(css_uri_list)
        if os.path.isfile('%s.css' % filepath):
            css_requires.append(self.getResourceUri('%s.css' % filepath, add_mtime=True))
        if os.path.isfile(self.resolvePath('%s.css' % self.pagename)):
            css_requires.append('%s.css' % self.pagename)
        return css_requires, css_media_requires

    def getResourceList(self, path, ext=None):
        """TODO

        :param path: TODO
        :param ext: TODO"""
        return self.site.resource_loader.getResourceList(self.resourceDirs, path, ext=ext)

    def getResourceUriList(self, path, ext=None, add_mtime=False):
        """TODO

        :param path: TODO
        :param ext: TODO
        :param add_mtime: TODO"""
        flist = self.getResourceList(path, ext=ext)
        return [self.resolveResourceUri(f, add_mtime=add_mtime) for f in flist]

    def getResourceExternalUriList(self, path, ext=None, add_mtime=False):
        """TODO

        :param path: TODO
        :param ext: TODO
        :param add_mtime: TODO"""
        flist = self.getResourceList(path, ext=ext)
        return [self.externalUrl(self.resolveResourceUri(f, add_mtime=add_mtime)) for f in flist]

    def onServingCss(self, css_requires):
        """TODO

        :param css_requires: the :ref:`"css_requires" webpage variable <css_requires>`"""
        pass


    def getResourceUri(self, path, ext=None, add_mtime=False, pkg=None):
        """TODO

        :param path: MANDATORY. A string with the path of the uri
        :param ext: TODO
        :param add_mtime: TODO
        :param pkg: the :ref:`package <packages>` object"""
        if path and path.startswith('/'):
            lpath = path.split('/')[1:]   
            if self.site.getStatic(lpath[0][1:]):
                path = self.site.getStatic(lpath[0][1:]).path(*lpath[1:])
        fpath = self.getResource(path, ext=ext,pkg=pkg)
        if not fpath:
            return
        return self.resolveResourceUri(fpath, add_mtime=add_mtime,pkg=pkg)


    def resolveResourceUri(self, fpath, add_mtime=False, pkg=None):
        """TODO

        :param fpath: TODO
        :param add_mtime: TODO
        :param pkg: the :ref:`package <packages>` object"""
        url = None 
        packageFolder = self.site.getPackageFolder(pkg) if pkg else self.package_folder
        pkg = pkg or self.packageId  
        if fpath.startswith(self.site.site_path):
            uripath = fpath[len(self.site.site_path):].lstrip('/').split(os.path.sep)
            url = self.site.storage('site').url(*uripath)
        elif fpath.startswith(self.site.pages_dir):
            uripath = fpath[len(self.site.pages_dir):].lstrip('/').split(os.path.sep)
            url = self.site.storage('pages').url(*uripath)
        elif fpath.startswith(packageFolder):
            uripath = fpath[len(packageFolder):].lstrip('/').split(os.path.sep)
            url = self.site.storage('pkg').url(pkg, *uripath)
        else:
            for rsrc, rsrc_path in list(self.site.resources.items()):
                if fpath.startswith(rsrc_path):
                    uripath = fpath[len(rsrc_path):].lstrip('/').split(os.path.sep)
                    url = self.site.storage('rsrc').url(rsrc, *uripath)
                    break
        if url and add_mtime:
            mtime = os.stat(fpath).st_mtime
            url = '%s?mtime=%0.0f' % (url, mtime)
        return url
    
    def packageResourcePath(self,table=None,filepath=None,custom=False,forcedPackage=None):
        table_pkg = None
        if table:
            table_pkg,tblname = table.split('.')
            respath = 'tables/%s/%s' %(tblname,filepath)
        else:
            respath = filepath
        if custom:
            return os.path.join(self.site.site_path, '_custom', self.package.name, '_resources',respath)
        packageFolder = self.site.gnrapp.packages[table_pkg].packageFolder
        if forcedPackage and forcedPackage!=table_pkg:
            packageFolder = self.site.gnrapp.packages[forcedPackage].packageFolder
            respath = 'tables/_packages/%s/%s/%s' %(table_pkg,tblname,filepath)        
        return os.path.join(packageFolder,'resources',respath)
            
    def getResource(self, path, ext=None, pkg=None):
        """TODO
        
        :param path: TODO
        :param ext: TODO
        :param pkg: the :ref:`package <packages>` object"""
        resourceDirs = self.resourceDirs
        if pkg:
            resourceDirs = self.site.resource_loader.package_resourceDirs(pkg)
        result = self.site.resource_loader.getResourceList(resourceDirs, path, ext=ext)
        if result:
            return result[0]
            
    getResourcePath = getResource

    def loadResourceScript(self,path,pkg=None,class_name=None,importAs=None):
        if pkg=='*':
            pkg = None
        class_name = class_name or 'Main'
        cl = self.importResource(path,classname=class_name,pkg=pkg,importAs=importAs)
        return cl(page=self)
        
            
    def importResource(self, path, classname=None, pkg=None,importAs=None):
        """TODO
        
        :param path: TODO
        :param classname: TODO
        :param pkg: the :ref:`package <packages>` object"""
        res = self.getResource(path,pkg=pkg,ext='py')
        if res:
            m = gnrImport(res,importAs=importAs)
            if not m:
                raise GnrMissingResourceException('Missing resource %(resource_path)s',resource_path=path)
            if classname:
                cl = getattr(m,classname,None)
                if cl:
                    cl._gnrPublicName = '_resourcescript.%s.%s.%s' %(pkg or '*',path,classname)
                    return cl
                raise GnrMissingResourceException('Missing resource %(classname)s in %(resource_path)s',resource_path=path,classname=classname)
            return m
        
    def importTableResource(self, table, path):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param path: the table resource path"""
        pkg,table = table.split('.')
        path,classname= path.split(':')
        try:
            resource = self.importResource('tables/_packages/%s/%s/%s' %(pkg,table,path),classname=classname,pkg=self.packageId,importAs='%s_packages_%s_%s_%s' %(self.packageId,pkg,table,path))
        except GnrMissingResourceException:
            resource = None
        if not resource:
            resource = self.importResource('tables/%s/%s' %(table,path),classname=classname,pkg=pkg)
        if not resource:
            resource = self.importResource('tables/_default/%s' %path,classname=classname,pkg=pkg)
        return resource
        
    @public_method
    def getResourceContent(self, resource=None, ext=None, pkg=None):
        """TODO
        
        ``getResourceContent()`` method is decorated with the :meth:`public_method <gnr.core.gnrdecorator.public_method>` decorator
        
        :param resource: TODO
        :param ext: TODO
        :param pkg: the :ref:`package <packages>` object"""
        content,path =  self._getResourceContent(resource=resource,ext=ext,pkg=pkg)
        return content
        
    def _getResourceContent(self, resource=None, ext=None, pkg=None):
        if not isinstance(ext,list):
            ext = [ext]
        for e in ext:
            path = self.getResource(path=resource,ext=e,pkg=pkg)
            if path:
                break
        if not path:
            return None,None
        with open(path) as f:
            result = f.read()
        return result,path

    @public_method
    def getTableResourceContent(self,table=None,path=None,value=None,ext=None,contentOnly=None):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param path: TODO
        :param value: TODO
        :param ext: TODO"""
        pkg,table = table.split('.')    
        resourceContent,respath = self._getResourceContent(resource='tables/_packages/%s/%s/%s' %(pkg,table,path),pkg=self.package.name,ext=ext)
        if not resourceContent:
            resourceContent,respath = self._getResourceContent(resource='tables/%s/%s' %(table,path),pkg=pkg,ext=ext)
        return resourceContent if contentOnly else (resourceContent,respath)
        
    def setTableResourceContent(self,table=None,path=None,value=None,ext=None):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param path: TODO
        :param value: TODO
        :param ext: TODO"""
        pkg,table = table.split('.')
        path = '%s.%s' %(path,ext)
        
        if isinstance(value,Bag):
            value = value.toXml(autocreate=True,addBagTypeAttr=False,typeattrs=False)
        with self.site.storage('pkg').open(pkg,'tables',table,path,mode='w') as f:
            f.write(value)

    def callTableScript(self, page=None, table=None, respath=None, class_name=None, runKwargs=None,returnURL=False, **kwargs):
        """Call a script from a table's resources (e.g: ``_resources/tables/<table>/<respath>``).

        This is typically used to customize prints and batch jobs for a particular installation

        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param respath: TODO
        :param class_name: TODO
        :param runKwargs: TODO"""
        script = self.loadTableScript(table=table, respath=respath, class_name=class_name)
        if runKwargs:
            for k, v in list(runKwargs.items()):
                kwargs[str(k)] = v
        result = script(**kwargs)
        return result

    def loadTableScript(self, table=None, respath=None, class_name=None,**kwargs):
        """TODO

        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param respath: TODO
        :param class_name: TODO"""
        return self.site.loadTableScript(self, table=table, respath=respath, class_name=class_name,**kwargs)
        
    @public_method
    def setPreference(self, path, data, pkg=''):
        """TODO
        
        :param path: TODO
        :param data: TODO
        :param pkg: the :ref:`package <packages>` object"""
        self.site.setPreference(path, data, pkg=pkg)
        
    def getPreference(self, path, pkg=None, dflt=None, mandatoryMsg=None):
        """TODO
        
        :param path: TODO
        :param pkg: the :ref:`package <packages>` object
        :param dflt: TODO"""
        return self.site.getPreference(path, pkg=pkg, dflt=dflt, mandatoryMsg=mandatoryMsg)
       
    @public_method 
    def getUserPreference(self, path='*', pkg=None, dflt=None, username=None,**kwargs):
        """TODO
        
        :param path: TODO
        :param pkg: the :ref:`package <packages>` object
        :param dflt: TODO
        :param username: TODO"""
        if not username and self.isGuest:
            return
        return self.site.getUserPreference(path, pkg=pkg, dflt=dflt, username=username)
        
    @public_method
    def getAppPreference(self,pkg=None,**kwargs):
        """TODO
        
        :param path: TODO"""
        path = kwargs.get('path') or kwargs.get('prefpath') or '*'
        app_preference = self.getPreference(path,pkg=pkg)
        owner_name = app_preference['adm.instance_data.owner_name']
        if not owner_name:
            app_preference['adm.instance_data.owner_name'] = app_preference['adm.gui_customization.owner.owner_name']
        return app_preference

    @public_method
    def setUserPreference(self, path, data, pkg='', username=''):
        """TODO
        
        :param path: TODO
        :param data: TODO
        :param pkg: the :ref:`package <packages>` object
        :param username: TODO"""
        self.site.setUserPreference(path, data, pkg=pkg, username=username)
        
    @public_method
    def getShortcuts(self,**kwargs):
        shortcuts = self.db.table('adm.shortcut').query().fetch()
        result = Bag()
        for i,r in enumerate(shortcuts):
            result.setItem('r_%i' %i,None,phrase=r['phrase'],groupcode=r['groupcode'],keycode=r['keycode'])
        return result

    def clientPublish(self,topic,nodeId=None,iframe=None,parent=None,page_id=None,**kwargs):
        for k,v in kwargs.items():
            if isinstance(v,Bag):
                v = self.catalog.asTypedText(v)
                kwargs[k] = v
        if self.wsk_enabled:
            self.wsk.publishToClient(page_id or self.page_id,topic=topic,data=kwargs,nodeId=nodeId,iframe=iframe)
        else:
            value = dict(topic=topic,kw=kwargs)
            if nodeId:
                value['nodeId'] = nodeId
            if iframe:
                value['iframe'] = iframe
            if parent:
                value['parent'] = parent
            self.setInClientData('gnr.publisher',value=value,page_id=page_id,fired=True)

    def setInClientRecord(self,tblobj=None,record=None,fields=None,silent=True):
        updater = Bag()
        for field in fields.split(','):
            updater[field] = record[field]
        self.clientPublish('setInClientRecord',table=tblobj.fullname,
                            pkey=record[tblobj.pkey],silent=silent,
                            updater=updater)
        
    def setInClientData(self, path, value=None, attributes=None, page_id=None, filters=None,
                        fired=False, reason=None, replace=False,public=None,**kwargs):
        
        if self.wsk_enabled or hasattr(self,'asyncServer'):
            try:
                self.setInClientData_websocket(path, value=value, attributes=attributes, page_id=page_id or self.page_id, filters=filters,
                        fired=fired, reason=reason, replace=replace,public=public,**kwargs)
                return
            except Exception:
                if False: # raise in certi casi
                    raise
                pass
        self.setInClientData_legacy(path, value=value, attributes=attributes, page_id=page_id or self.page_id, filters=filters,
                        fired=fired, reason=reason, replace=replace,public=public,**kwargs)

    def notifyLocalDbEvents(self,dbeventsDict=None,origin_page_id=None,dbevent_reason=None):
        for table,dbevents in list(dbeventsDict.items()):
            if not dbevents:
                continue
            table_code = table.replace('.', '_')
            self.addLocalDatachange('gnr.dbchanges.%s' %table_code, dbevents,attributes=dict(from_page_id=origin_page_id,dbevent_reason=dbevent_reason))


    def addLocalDatachange(self, path, value=None, attributes=None, fired=False, reason=None, delete=False):
        datachange = ClientDataChange(path, value, attributes=attributes, fired=fired,
                                      reason=reason, delete=delete)
        self.local_datachanges.append(datachange)

    def setInClientData_legacy(self, path, value=None, attributes=None, page_id=None, filters=None,
                        fired=False, reason=None, replace=False,public=None,**kwargs):
        if public or filters or page_id:
            self.site.register.setInClientData(path=path, value=value, attributes=attributes, page_id=page_id or self.page_id, filters=filters,
                        fired=fired, reason=reason, replace=replace,register_name='page')
        elif isinstance(path, Bag):
            changeBag = path
            for changeNode in changeBag:
                attr = changeNode.attr
                datachange = ClientDataChange(attr.pop('_client_path'), changeNode.value,
                    attributes=attr, fired=attr.pop('fired', None))
                self.local_datachanges.append(datachange)
        else:
            datachange = ClientDataChange(path, value, reason=reason, attributes=attributes, fired=fired)
            self.local_datachanges.append(datachange)
            
    def setInClientData_websocket(self, path, value=None, attributes=None, page_id=None, filters=None,
                        fired=False, reason=None, replace=False,public=None,nodeId=None,noTrigger=None,**kwargs):
        page_id = page_id or self.page_id
        if filters:
            page_id = list(self.site.register.pages(filters=filters).keys())
        if isinstance(path, Bag):
            changeBag = path
            for changeNode in changeBag:
                attr = changeNode.attr
                self.wsk.setInClientData(page_id=page_id,path=attr.pop('_client_path'),value=changeNode.value,
                    attributes=attr,fired=attr.pop('fired', None),reason=reason,noTrigger=noTrigger,nodeId=nodeId)
        else:
            self.wsk.setInClientData(page_id=page_id,path=path,value=value,attributes=attributes,
                                        fired=fired,reason=reason,nodeId=nodeId,noTrigger=noTrigger)


    @public_method          
    def sendMessageToClient(self, message, pageId=None, filters=None, msg_path=None, fired=None,title=None):
        self.setInClientData(msg_path or 'gnr.servermsg', message,fired=fired,
                                         page_id=pageId, filters=filters,
                                         attributes=dict(from_user=self.user, from_page=self.page_id,
                                                         title=title))

        


    @public_method
    def chatMessageToUser(self,msg=None,user=None,from_user=None,roomId=None,priority=None,disconnect=None,users=None,sysmessage=False):
        if sysmessage:
            from_user = 'SYSTEM'
            roomId = 'cr_system_message'
        else:
            from_user = from_user or  self.user
            roomId = roomId or 'cr_%s' %self.getUuid()
        path = 'gnr.chat.msg.%s' % roomId
        priority = priority or 'H'
        if not users:
            users = Bag()
            if from_user!='SYSTEM':
                users.setItem(from_user,None,user_name=from_user,user=from_user)
            users.setItem(user,None,user_name=user,user=user)
        ts = self.toText(datetime.datetime.now(), format='HH:mm:ss')
        with self.userStore(user) as store:
            if disconnect and (user == from_user):
                store.drop_datachanges(path)
            else:
                in_out = 'in' if user != from_user else 'out'
                value = Bag(dict(msg=msg, roomId=roomId, users=users, roomtitle='System messages',from_user=from_user,
                                 in_out=in_out, ts=ts, disconnect=disconnect))
                store.set_datachange(path, value, fired=True, reason='chat_out')
        self.setInClientData(path='gnr.chat.room_alert', value=Bag(dict(roomId=roomId, users=users, priority=priority,roomtitle='System piero')),
                                     filters='user:%s' % user, fired=True, reason='chat_open',
                                     public=True, replace=True)#

    def _get_package_folder(self):
        if not hasattr(self, '_package_folder'):
            self._package_folder = self.site.getPackageFolder(self.packageId)
        return self._package_folder
    package_folder = property(_get_package_folder)
    
    def rpc_main(self, _auth=AUTH_OK, debugger=None,windowTitle=None,_parent_page_id=None,_root_page_id=None,branchIdentifier=None, **kwargs):
        """The first method loaded in a Genro application
        
        :param _auth: the page authorizations. For more information, check the :ref:`auth` page
        :param debugger: TODO"""
        page = self.domSrcFactory.makeRoot(self)
        self._root = page
        pageattr = {}
        self.parent_page_id = _parent_page_id
        self.root_page_id = _root_page_id
        rootenv = self.getStartRootenv()
        self._workdate = None #reset workdate
        prefenv = Bag()
        has_adm = self.application.db.package('adm')
        if has_adm:
            prefenv = self.application.db.table('adm.preference').envPreferences(username=self.user)
        data = Bag(dict(root_page_id=self.root_page_id,parent_page_id=self.parent_page_id,rootenv=rootenv,prefenv=prefenv))
        self.pageStore().update(data)
        self._db = None #resetting db property after setting dbenv
        google_mapkey = self.application.config['google?mapkey']
        api_keys = Bag(self.application.config['api_keys'])
        if 'google' not in api_keys and google_mapkey:
            api_keys.setItem('google',None,mapkey = google_mapkey)
        page.data('gnr.api_keys',api_keys)
        if hasattr(self, 'main_root'):
            self.main_root(page, **kwargs)
            return (page, pageattr)
        page.data('gnr.windowTitle',windowTitle or self.windowTitle())
        page.data('gnr.developerToolsVisible',False)
        page.dataController("""
                            genro.dom.setClass(document.body,'developerToolElementsVisible',developerToolsVisible)""",
                            developerToolsVisible='^gnr.developerToolsVisible')
        page.dataController("""genro.src.updatePageSource('_pageRoot')""",
                        subscribe_gnrIde_rebuildPage=True,_delay=100)
        page.dataController("PUBLISH setWindowTitle=windowTitle;",windowTitle="^gnr.windowTitle",_onStart=True)
        page.dataRemote('server.pageStore',self.getPageStoreData,cacheTime=1)
        if branchIdentifier:
            page.dataController(""" let b = new gnr.GnrBag();
                                    b.setCallBackItem('root',genro.getParentBranchMenuByIdentifier,{branchIdentifier:branchIdentifier});
                                    SET gnr.parentBranchMenu = b;
                                """,branchIdentifier=branchIdentifier,_onStart=True)

        page.dataRemote('server.dbEnv',self.dbCurrentEnv,cacheTime=1)
        page.dataController(""" var changelist = copyArray(_node._value);
                                dojo.forEach(changelist,function(c){
                                    for (var k in c){
                                        c[k] = convertFromText(c[k]);
                                    }
                                })
                                genro.publish('dbevent_'+_node.label,{'changelist':changelist,'changeattr':_node.attr});""",
                                changes="^gnr.dbchanges")
        page.data('gnr.homepage', self.externalUrl(self.site.homepage))
        page.data('gnr.homeFolder', self.externalUrl(self.site.home_uri).rstrip('/'))
        page.data('gnr.homeUrl', self.site.home_uri)
        page.data('gnr.defaultUrl', self.site.default_uri)
        page.data('gnr.siteName',self.siteName)
        page.data('gnr.page_id',self.page_id)
        page.data('gnr.package',self.package.name)
        page.data('gnr.root_page_id',self.root_page_id)
        page.data('gnr.workdate', self.workdate) #serverpath='rootenv.workdate')
        page.data('gnr.language', self.language,serverpath='rootenv.language',dbenv=True)
        
        page.data('gnr.table',getattr(self,'maintable',None))
        page.data('gnr.project_code',self.db.application.packages[self.package.name].project)

        page.dataController("""genro.publish({topic:'changedLanguage',iframe:'*',kw:{lang:language}})""",language='^gnr.language')
        page.dataController('SET gnr.language = lang;',subscribe_changedLanguage=True)
        #page.data('gnr.userTags', self.userTags)
        page.data('gnr.locale', self.locale)
        page.data('gnr.pagename', self.pagename)
        page.data('gnr.remote_db',self.site.remote_db)
        if self.dbstore:
            page.data('gnr.dbstore',self.dbstore)
        if has_adm and not self.isGuest:
            page.dataRemote('gnr.user_preference', self.getUserPreference,username='^gnr.avatar.user',
                            _resolved=True,_resolved_username=self.user)
            page.dataRemote('gnr.app_preference', self.getAppPreference,_resolved=True)
            page.dataRemote('gnr.shortcuts.store', self.getShortcuts)

       #page.dataController("""
       #    var rotate_val = user_theme_filter_rotate || app_theme_filter_rotate || 0;
       #    var invert_val = user_theme_filter_invert || app_theme_filter_invert || 0;
       #    var kw = {'rotate':rotate_val,'invert':invert_val};
       #    var styledict = {font_family:app_theme_font_family,font_size:app_theme_font_size,zoom:app_theme_zoom};
       #    genro.dom.css3style_filter(null,kw,styledict);
       #    dojo.style(dojo.body(),styledict);
       #    """,app_theme_filter_rotate='^gnr.app_preference.sys.theme.body.filter_rotate',
       #        user_theme_filter_rotate='^gnr.user_preference.sys.theme.body.filter_rotate',
       #        app_theme_filter_invert='^gnr.app_preference.sys.theme.body.filter_invert',
       #        app_theme_zoom='^gnr.app_preference.sys.theme.body.zoom',

       #        user_theme_filter_invert='^gnr.user_preference.sys.theme.body.filter_invert',
       #        app_theme_font_family='^gnr.app_preference.sys.theme.body.font_family',
       #    app_theme_font_size='^gnr.app_preference.sys.theme.body.font_size',

       #        _onStart=True)



        page.dataController('genro.dlg.serverMessage("gnr.servermsg");', _fired='^gnr.servermsg')
        #page.dataController("genro.dom.setClass(dojo.body(),'bordered_icons',bordered);",
        #            bordered="^gnr.user_preference.sys.theme.bordered_icons",_onStart=True)
        rspath = '^gnr.user_preference.sys.theme.mobile' if self.isMobile else '^gnr.user_preference.sys.theme.desktop'
        page.dataController("""genro.dom.setRootStyle(rs);""", rs=rspath, _if='rs', _onStart=True)   
        page.dataController("genro.getDataNode(nodePath).refresh(true);",
                            nodePath="^gnr.serverEvent.refreshNode")
                            
        page.dataController("""if(kw){
                                genro.publish(kw);
                             };""", kw='^gnr.publisher')

        page.dataController('if(url){genro.download(url)};', url='^gnr.downloadurl')
        page.dataController("""if(url){
                                genro.download(url,null,"print")
                                };""", url='^gnr.printurl')
        page.dataController("""
                genro.playUrl(url);
            """,url='^gnr.playUrl')
        page.dataRpc(None,self.quickCommunication,subscribe_quick_comunication=True,
                    _onResult='genro.publish("quick_comunication_sent",{info:result});')

        page.dataController("genro.openWindow(url,filename);",url='^gnr.clientprint',filename='!!Print')
                                
        page.dataController('funcCreate(msg)();', msg='^gnr.servercode')
        page.dock(id='dummyDock',display='none')

        root = page.borderContainer(design='sidebar', position='absolute',top=0,left=0,right=0,bottom=0,
                                    nodeId='_gnrRoot',subscribe_floating_message='genro.dlg.floatingMessage(this,$1);')
        
        typekit_code = self.site.config['gui?typekit']
        if typekit_code and False:
            page.script(src="http://use.typekit.com/%s.js" % typekit_code)
            page.dataController("try{Typekit.load();}catch(e){}", _onStart=True)
        root.div(id='auxDragImage')
        root.div(id='srcHighlighter')
        pageOptions = self.pageOptions or dict()
        clientCachedRecord = pageOptions.get('clientCachedRecord')
        if clientCachedRecord:
            for table in clientCachedRecord.split(','):
                root.data('gnr.cachedRecord.%s' %table,None,
                            serverpath=self.db.table(table).cachedKey('cachedRecord'))
        context_subtables = pageOptions.get('context_subtables')
        if context_subtables:
            root.data('gnr.context_subtables',Bag(context_subtables),dbenv=True,serverpath='rootenv.context_subtables')
        if self.root_page_id and self.root_page_id==self.parent_page_id:
            root.dataController("""
                               if(openMenu===false){
                                    genro.publish({parent:true,topic:'setIndexLeftStatus'},openMenu);
                               }
                               """,
                            _onStart=True,openMenu=pageOptions.get('openMenu',True))   
        if _auth == AUTH_OK:            
            _auth = self._checkRootPage()
        if _auth == AUTH_OK:
            main_call = kwargs.pop('main_call', None)
            if main_call:
                main_handler = self.getPublicMethod('rpc',main_call) 
                if main_handler:
                    main_handler(root.contentPane(region='center',nodeId='_pageRoot'),**kwargs)
            else:
                rootwdg = self.rootWidget(root, region='center', nodeId='_pageRoot')
                if getattr(self,'mainWrapper',None):
                    self.mainWrapper(rootwdg, **kwargs)
                else:
                    self.main(rootwdg, **kwargs)
            self.onMainCalls()
            if hasattr(self,'deferredMainPageAuthTags'):
                _auth = AUTH_OK if self.deferredMainPageAuthTags(page) else AUTH_FORBIDDEN
        if _auth == AUTH_NOT_LOGGED:
            root.clear()
            self.mixinComponent('login:LoginComponent',safeMode=True,only_callables=False)
            self.loginDialog(root, **kwargs)
        elif _auth == AUTH_FORBIDDEN:
            redirect = self.forbiddenRedirectPage
            if redirect:
                params = urllib.parse.urlencode(self.pageArgs)
                if params:
                    redirect = '%s?%s' % (redirect, params)
                return (page,dict(redirect=redirect))
            self.forbiddenPage(root, **kwargs)
        if not self.isGuest:
            self.site.pageLog('open')
        if self.avatar:
            page.data('gnr.avatar', Bag(self.avatar.as_dict()))
        page.data('gnr.rootenv',self.rootenv)
        page.data('gnr.polling.user_polling', self.user_polling)
        page.data('gnr.polling.auto_polling', self.auto_polling)
        pageArgs = self.pageArgs
        if 'polling_enabled' in pageArgs:
            polling_enabled = boolean(pageArgs['polling_enabled'])
        else:
            polling_enabled = True
        page.data('gnr.polling.polling_enabled', polling_enabled)
        page.dataController("""genro.user_polling = user_polling;
                               genro.auto_polling = auto_polling;
                               genro.polling_enabled = polling_enabled;
                              """,
                            user_polling="^gnr.polling.user_polling",
                            auto_polling="^gnr.polling.auto_polling",
                            polling_enabled="^gnr.polling.polling_enabled",
                            _init=True)
        if self._pendingContext:
            self.site.register.setPendingContext(self.page_id,self._pendingContext,register_name='page')            

        #if self.wsk:
        #    page_item_data = self.page_item['data']
        #    page_info = page_item_data['page_info']
        #    class_info = page_item_data['class_info']
        #    init_info = page_item_data['init_info']
        #    mixin_set = getattr(self,'mixin_set',[])
        #    registerNewPageData = Bag(dict(page_id=self.page_id,page_info=page_info,class_info=class_info,init_info=init_info,mixin_set=mixin_set))
        #    self.wsk.sendCommandToPage('','registerNewPage',registerNewPageData)
        return (page, pageattr)
   
    def loginDialog(self, root, **kwargs):
        """TODO
        
        :param root: the root of the page. For more information, check the
                     :ref:`webpages_main` section"""
        dlg = root.dialog(toggle="fade", toggleDuration=250, onCreated='widget.show();')
        #f = dlg.form()
        #f.div(content='Forbidden Page', text_align="center", font_size='24pt')
        tbl = dlg.contentPane(_class='dojoDialogInner').table()
        row = tbl.tr()
        row.td(content='Sorry. You are not allowed to use this page.', align="center", font_size='16pt',
               color='#c90031')
        cell = tbl.tr().td()
        cell.div(float='right', padding='2px').button('Back', action='genro.pageBack()')

    def forbiddenPage(self, root,msg=None, **kwargs):
        """
        :param root: the root of the page. For more information, check the
                     :ref:`webpages_main` section"""
        root.clear()
        box = root.div(position='absolute',top=0,left=0,right=0,bottom='20px')
        box.iframe(height='100%', width='100%', src=self.getResourceUri('html_pages/forbidden.html'), border='0px') 
        root.lightbutton('Logout',action='genro.logout()',position='absolute',bottom='10px',right='10px',cursor='pointer',
                         font_weight='bold')
        

    def getStartRootenv(self):
        #cookie = self.get_cookie('%s_dying_%s_%s' %(self.siteName,self.packageId,self.pagename), 'simple')
        #if cookie:
        #    return Bag(urllib.unquote(cookie.value)).getItem('rootenv')
        currenv = self.pageStore(page_id=self.parent_page_id or self.page_id).getItem('rootenv') or Bag()
        if not self.root_page_id and not currenv['new_window_context']: 
            # page not in framedindex or framedindex itself and not windowcontext
            # get the connections defaults
            connectionStore = self.connectionStore()
            defaultRootenv = Bag(connectionStore.getItem('defaultRootenv'))
            if '_workdate' in self._call_kwargs:
                defaultRootenv['workdate'] = self.catalog.fromText(self._call_kwargs['_workdate'],'D')
            return defaultRootenv
        return currenv
        

    def onMain(self): #You CAN override this !
        """TODO"""
        pass


    @public_method    
    def getPageStoreData(self):
        """TODO"""
        return self.pageStore().getItem('')

    @public_method    
    def getUserStoreData(self):
        """TODO"""
        return self.userStore().getItem('')

                                            
    def onMainCalls(self):
        """TODO"""
        calls = [m for m in dir(self) if m.startswith('onMain_') and not m.endswith('_')]
        for m in calls:
            getattr(self, m)()
        self.onMain()
        
    def rpc_onClosePage(self, **kwargs):
        """An rpc on page closure"""
        self.onClosePage()
        self.site.onClosePage(self)
        
    def onClosePage(self):
        """TODO"""
        pass
        
    def pageFolderRemove(self):
        """TODO"""
        shutil.rmtree(os.path.join(self.connectionFolder, self.page_id), True)
        
    def rpc_callTableScript(self, table=None, respath=None, class_name='Main', downloadAs=None,resultAs=None, **kwargs):
        """Call a script from a table's local resources (i.e. ``_resources/tables/<table>/<respath>``).
        
        This is typically used to customize prints and batch jobs for a particular installation.
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param respath: TODO
        :param class_name: TODO
        :param downloadAs: TODO"""
        if downloadAs:
            self.download_name = downloadAs
        result = self.site.callTableScript(page=self, table=table, respath=respath, class_name=class_name,
                                         downloadAs=downloadAs,resultAs=resultAs, **kwargs)
        if not result:
            return None
        if (resultAs is None or resultAs=='path') and os.path.exists(result):
            return open(result,'r')
        return result

    @public_method
    def bagFieldDispatcher(self,pane,resource=None,module=None,table=None,
                        bfhandler=None,field=None,version=None,valuepath=None,**kwargs):
        if bfhandler:
            handlername = bfhandler
        else:
            handlername = 'bf_{field}'.format(field=field)
        if resource:
            if ':' not in resource:
                resource = '{resource}:BagField_{field}'.format(resource=resource,field=field)
                handlername = 'bf_main'
            if table:
                mixinedClass = self.mixinTableResource(table,'bagfields/{resource}'.format(resource=resource))
            else:
                mixinedClass = self.mixinComponent(resource)
        bagfieldmodule = getattr(mixinedClass,'__top_mixined_module',None)
        box = pane.contentPane(datapath=valuepath,bagfieldmodule=bagfieldmodule)
        return getattr(self,handlername)(box,**kwargs)
        
    
    @public_method                                 
    def remoteBuilder(self, handler=None,tag=None, py_requires=None,_inheritedAttributes=None,**kwargs):
        """TODO
        
        :param handler: TODO"""
        if py_requires:
            for p in py_requires.split(','):
                self.mixinComponent(p)
        if tag:
            def handler(root,**pars):
                root.child(tag,**pars)
        else:
            handler = self.getPublicMethod('remote', handler)
        if handler:
            pane = self.newSourceRoot(_inheritedAttributes)
            self._root = pane
            for k, v in list(kwargs.items()):
                if k.endswith('_path'):
                    kwargs[k[0:-5]] = kwargs.pop(k)[1:]
            handler(pane, **kwargs)
            return pane
        
            
    def rpc_ping(self, **kwargs):
        """TODO"""
        pass
        
    def rpc_setInServer(self, path, value=None, pageId=None, **kwargs):
        """TODO
        
        :param path: TODO
        :param value: TODO. 
        :param pageId: TODO. """
        self.pageStore(pageId).setItem(path, value)
            
    #def rpc_setViewColumns(self, contextTable=None, gridId=None, relation_path=None, contextName=None,
    #                       query_columns=None, **kwargs):
    #    self.app.setContextJoinColumns(table=contextTable, contextName=contextName, reason=gridId,
    #                                   path=relation_path, columns=query_columns)
         
    def rpc_getPrinters(self):
        """TODO"""
        networkprint = self.getService('networkprint')
        if networkprint:
            return networkprint.getPrinters()
            
    def rpc_getPrinterAttributes(self, printer_name,**kwargs):
        """TODO
        
        :param printer_name: TODO"""
        if printer_name and printer_name != 'PDF':
            attributes = self.getService('networkprint').getPrinterAttributes(printer_name)
            return attributes

    def windowTitle(self):
        """Return the window title"""
        return getattr(self,'window_title',None) or os.path.splitext(os.path.basename(self.filename))[0].replace('_', ' ').capitalize()

    @public_method
    def subfieldExplorer(self,table=None,field=None, fieldvalue=None,prevRelation='', prevCaption='',
                             omit='', recordpath=None,**kwargs):
        df_table = self.db.table(table).column(field).relatedTable().dbtable
        subfields = df_table.df_subFieldsBag(pkey=fieldvalue,df_field=prevRelation,df_caption=prevCaption)
        if  df_table.model.column('df_custom_templates') is not None:
            df_custom_templates = df_table.readColumns(pkey=fieldvalue,columns='$df_custom_templates')    
            df_custom_templates = Bag(df_custom_templates)
            for t in list(df_custom_templates.keys()):
                caption='Summary: %s' %t
                recordpath = recordpath or '@%s' %field
                fieldpath = '%s:%s.df_custom_templates.%s.tpl' %(prevRelation,recordpath,t)
                subfields.setItem('summary_%s' %t,None,caption=caption,dtype='T',fieldpath=fieldpath,
                                  fullcaption='%s/%s' %(prevCaption,caption))
        return subfields

    @public_method    
    def quickCommunication(self,message=None,email=None,fax=None,mobile=None):
        result = 'Communication not supported'
        if email:
            subject = message.split('\n')[0]
            result = self.getService('mail').sendmail(to_address=email,
                                    body=message, subject=subject,
                                    async_=False)
        elif mobile:
            result = self.getService('sms').sendsms(receivers=mobile,data=message)
        elif fax:
            result = self.getService('fax').sendfax(receivers=fax,message=message)
        return result or True

    @public_method
    def relationExplorer(self,table=None,item_type=None,checkPermissions=None,**kwargs):
        if checkPermissions is True:
            checkPermissions = self.permissionPars
        if item_type:
            userConfig = self.getUserTableConfig(table=table)
            item_code = userConfig[item_type.lower()]
            if item_code is None:
                return self.dbRelationExplorerFull(table,checkPermissions=checkPermissions,**kwargs)
            elif item_code == '_RAW_':
                return self.dbRelationExplorerFull(table,checkPermissions=checkPermissions)
            elif item_code == '_NO_':
                return Bag()
            item = self.db.table('adm.tblinfo_item').getInfoItem(item_type=item_type,tbl=table,code=item_code)
            if item:
                return Bag(item['data'])['root']

        return self.dbRelationExplorerFull(table,checkPermissions=checkPermissions,**kwargs)

    def dbRelationExplorerFull(self, table=None, currRecordPath=None,prevRelation='', prevCaption='',
                             omit='',relationStack='', checkPermissions=None,**kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param prevRelation: TODO
        :param prevCaption: TODO
        :param omit: TODO"""
        if not table:
            return Bag()
        cps = 'false' if not checkPermissions else 'true'
        
        def buildLinkResolver(node, prevRelation, prevCaption,relationStack):
            nodeattr = node.getAttr()
            if  'name_long' not in nodeattr:
                raise Exception(nodeattr) # FIXME: use a specific exception class
            nodeattr['caption'] = nodeattr.pop('name_long')
            nodeattr.pop('tag',None)
            nodeattr['fullcaption'] = concat(prevCaption, self._(nodeattr['caption']), '/')

            if nodeattr.get('one_relation'):
                innerCurrRecordPath = '%s.%s' %(currRecordPath,node.label) if currRecordPath else ''
                nodeattr['_T'] = 'JS'
                if nodeattr['mode'] == 'O':
                    relpkg, reltbl, relfld = nodeattr['one_relation'].split('.')
                    relkey =  '%(many_relation)s/%(one_relation)s' %node.attr
                else:
                    relpkg, reltbl, relfld = nodeattr['many_relation'].split('.')
                    relkey =  '%(one_relation)s/%(many_relation)s' %node.attr
                relkey = str(hash(relkey) & 0xffffffff)
                jsresolver = "genro.rpc.remoteResolver('relationExplorer',{table:%s, prevRelation:%s, prevCaption:%s, omit:%s,currRecordPath:%s,relationStack:%s,checkPermissions:%s})"
                node.setValue(jsresolver % (
                jsquote("%s.%s" % (relpkg, reltbl)), jsquote(concat(prevRelation, node.label)),
                jsquote(nodeattr['fullcaption']), jsquote(omit),
                jsquote(innerCurrRecordPath),jsquote(concat(relationStack,relkey,'|')),cps
                ))
            elif 'subfields' in nodeattr:
                typecol = self.db.table(f'{nodeattr["pkg"]}.{nodeattr["table"]}').column(nodeattr["subfields"])
                if typecol is None:
                    self.log(f'warning missing column {nodeattr["subfields"]} used inside subfields attribute in table {nodeattr["pkg"]}.{nodeattr["table"]}')
                elif not currRecordPath:
                    default_templates = self.db.table(f'{nodeattr["pkg"]}.{nodeattr["table"]}'
                                        ).column(f'@{nodeattr["subfields"]}.df_custom_templates'
                                        ).attributes.get('templates')
                    if default_templates:
                        templatesbag = Bag()
                        node.value = templatesbag
                        for t in default_templates.split(','):
                            caption=f'Summary: {t}'
                            fieldpath = f'{node.label}:@{nodeattr["subfields"]}.df_custom_templates.{t}.tpl'
                            templatesbag.setItem(f'summary_{t}',None,caption=caption,dtype='T',fieldpath=fieldpath,
                                            fullcaption='%s/%s' %( nodeattr['caption'],caption),name_long=caption)
                else:
                    nodeattr['_T'] = 'JS'
                    jsresolver = "genro.rpc.remoteResolver('subfieldExplorer',{table:%s, field:%s,fieldvalue:%s,prevRelation:%s, prevCaption:%s, omit:%s,checkPermissions:%s},{cacheTime:1})"
                    node.setValue(jsresolver % (
                    jsquote("%(pkg)s.%(table)s" %nodeattr),
                    jsquote(nodeattr['subfields']),
                    jsquote("=%s.%s" %(currRecordPath,nodeattr['subfields'])),
                    jsquote(concat(prevRelation, node.label)),
                    jsquote(nodeattr['fullcaption']), jsquote(omit),cps))
                
            elif nodeattr.get('dtype')=='X' and currRecordPath:
                nodeattr['_T'] = 'JS'
                jsresolver ="""genro.dev.currDataExplorer({fieldPath:%s,prevRelation:%s,prevCaption:%s,omit:%s,checkPermissions:%s})""" 
                jsresolver = jsresolver %( jsquote("%s.%s" %(currRecordPath,node.label)),jsquote(concat(prevRelation, node.label)),jsquote(nodeattr['fullcaption']), jsquote(omit),cps)
                node.setValue(jsresolver)

        result = self.db.relationExplorer(table=table,
                                          prevRelation=prevRelation,
                                          relationStack=relationStack,
                                          omit=omit,checkPermissions=checkPermissions,
                                          **kwargs)
        result.walk(buildLinkResolver, prevRelation=prevRelation, prevCaption=prevCaption,relationStack=relationStack)
        return result
            
    def getAuxInstance(self, name):
        """TODO"""
        return self.site.getAuxInstance(name)
        
    def _get_connectionFolder(self):
        return os.path.join(self.site.allConnectionsFolder, self.connection_id)
        
    connectionFolder = property(_get_connectionFolder)
        
    def _get_userFolder(self):
        user = self.user or 'Anonymous'
        return os.path.join(self.site.allUsersFolder, user)
        
    userFolder = property(_get_userFolder)
    
    def temporaryDocument(self, *args):
        """TODO"""
        return self.connectionDocument('temp', *args)
        
    def temporaryDocumentUrl(self, *args, **kwargs):
        """TODO"""
        return self.connectionDocumentUrl('temp', *args, **kwargs)
        
    def connectionDocument(self, *args):
        """TODO"""
        filepath = os.path.join(self.connectionFolder, self.page_id, *args)
        folder = os.path.dirname(filepath)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return filepath
        
    def userDocument(self, *args):
        """TODO"""
        filepath = os.path.join(self.userFolder, *args)
        folder = os.path.dirname(filepath)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return filepath
        
    def connectionDocumentUrl(self, *args, **kwargs):
        """TODO"""
        if kwargs:
            return self.site.storage('conn').kwargs_url(self.connection_id, self.page_id, *args, **kwargs)
        else:
            return self.site.storage('conn').url(self.connection_id, self.page_id, *args)
            
    def userDocumentUrl(self, *args, **kwargs):
        """TODO"""
        if kwargs:
            return self.site.storage('user').kwargs_url(self.user, *args, **kwargs)
        else:
            return self.site.storage('user').url(self.user, *args)
    
    @public_method
    def moveUploadedFileToDestination(self,temp_path=None,dest_stn=None,
                                      dest_fld=None,dest_record_pkey=None,**kwargs):
        uploadedSn = self.site.storageNode(temp_path)
        if dest_fld:
            pkg,tbl,field = dest_fld.split('.')
            tblobj = self.db.table(f'{pkg}.{tbl}')
            column = tblobj.column(field)
            dest_stn = column.attributes['dest_stn']
            with tblobj.recordToUpdate(dest_record_pkey) as rec:
                rec[field] = f'{dest_stn.format(**rec.asDict())}.{uploadedSn.ext}'
            dest_stn = rec[field]
            self.setInClientRecord(tblobj=tblobj,record=rec,fields=field,silent=True)
        else:
            dest_stn = f'{dest_stn}.{uploadedSn.ext}'
        uploadedSn.move(dest_stn)
        if dest_fld:
            self.db.commit()
        return dest_stn
            
   
    @public_method
    def getSiteDocument(self,path,defaultContent=None,**kwargs):
        """TODO
        
        ``getSiteDocument()`` method is decorated with the :meth:`public_method <gnr.core.gnrdecorator.public_method>` decorator
        
        :param path: TODO
        :param defaultContent: TODO"""
        result = Bag()
        snode = self.site.storageNode(path)
        if not snode.exists:
            content = defaultContent
        else:
            if snode.ext=='xml':
                with snode.open('rb') as f:
                    content = Bag(f)
            elif snode.exists:
                with snode.open('rb') as f:
                    content = f.read()
            else:
                content = ''
        result.setItem('content',content)
        return result

    @public_method
    def saveSiteDocument(self,path=None,data=None,**kwargs):
        snode = self.site.storageNode(path)
        if snode.ext == 'xml':
            with snode.open('wb') as f:
                data.toXml(f)
        else:
            with snode.open('wb') as f:
                f.write(data['content'])
        return dict(savedPkey=path,path=path)

    @property
    def permissionPars(self):
        return dict(user=self.user,user_group=getattr(self.avatar,'group_code',None))
    
    @property
    def forbiddenRedirectPage(self):
        if hasattr(self,'forbidden_redirect'):
            return self.forbidden_redirect()
        if self.avatar and self.avatar.avatar_rootpage:
            return self.avatar.avatar_rootpage

    def isLocalizer(self):
        """TODO"""
        return self.hasTag('_TRD_')
    
    def isDeveloper(self):
        """TODO"""
        return self.hasTag('_DEV_')

        

    def hasTag(self,tag):
        if not self.userTags:
            return False
        return tag in self.userTags.split(',')
        
    # def addToContext_old(self, value=None, serverpath=None, clientpath=None):
    #     """TODO
    #     
    #     :param value: TODO
    #     :param serverpath: TODO
    #     :param clientpath: TODO"""
    #     self._pendingContextToCreate.append((value, serverpath, clientpath or serverpath))
      
    def addToContext(self,serverpath=None,value=None,attr=None):
        self._pendingContext.append((serverpath,value,dict(attr)))
        
        
    #def _createContext_old(self, root, pendingContext):
    #    with self.pageStore() as store:
    #        for value, serverpath, clientpath in pendingContext:
    #            store.setItem(serverpath, value)
    #    for value, serverpath, clientpath in pendingContext:
    #        root.child('data', __cls='bag', content=value, path=clientpath, _serverpath=serverpath)
    #        
    def setJoinCondition(self, ctxname, target_fld='*', from_fld='*', condition=None, one_one=None, applymethod=None,
                         **kwargs):
        """Define a join condition in a given context (*ctxname*).
        
        The *condition* attribute is used to limit the automatic selection of related records.
        If *target_fld* AND *from_fld* equals to '*' then the condition is an additional
        WHERE clause added to any selection
        
        ::
        
            self.setJoinCondition('mycontext',
                                   target_fld = 'mypkg.rows.document_id',
                                   from_fld = 'mypkg.document.id',
                                   condition = "mypkg.rows.date <= :wkd",
                                   condition_wkd = "^mydatacontext.foo.bar.mydate",
                                   one_one=False)
        
        :param ctxname: name of the context of the main record
        :param target_fld: the many table column of the :ref:`relation <relations>`;
                           '*' means the main table of the selection
        :param from_fld: the one table column of the :ref:`relation <relations>`;
                         '*' means the main table of the selection
        :param condition: additional :ref:`conditions <sql_condition>` for the WHERE sql condition
        :param one_one: the result is returned as a record instead of as a selection.
                        If one_one is True the given condition MUST return always a single record
        :param applymethod: a page method to be called after selecting the related records
        :param kwargs: named parameters to use in condition. Can be static values or can be readed
                       from the context at query time. If a parameter starts with '^' it is a path in
                       the context where the value is stored.
                       If a parameter is the name of a defined method the method is called and the result
                       is used as the parameter value. The method has to be defined as 'ctxname_methodname'"""
        path = '%s.%s_%s' % (ctxname, target_fld.replace('.', '_'), from_fld.replace('.', '_'))
        value = Bag(dict(target_fld=target_fld, from_fld=from_fld, condition=condition, one_one=one_one,
                         applymethod=applymethod, params=Bag(kwargs)))
        
        self._root.data('gnr.sqlctx.conditions.%s' % path,value, _serverpath='_sqlctx.conditions.%s' % path)
        #self.addToContext(value=value, serverpath='_sqlctx.conditions.%s' % path,
        #                  clientpath='gnr.sqlctx.conditions.%s' % path)
                          
   #def setJoinColumns(self, ctxname, target_fld, from_fld, joincolumns):
   #    path = '%s.%s_%s' % (ctxname, target_fld.replace('.', '_'), from_fld.replace('.', '_'))
   #    serverpath = '_sqlctx.columns.%s' % path
   #    clientpath = 'gnr.sqlctx.columns.%s' % path
   #    self.addToContext(value=joincolumns, serverpath=serverpath, clientpath=clientpath)
        
    def _prepareGridStruct(self,source=None,table=None,gridId=None):
        struct = None
        if isinstance(source, Bag):
            return source
        if gridId and not source:
            source = getattr(self, '%s_struct' % gridId,None)
        if callable(source): 
            struct = self.newGridStruct(maintable=table)
            source(struct)
            if hasattr(struct,'_missing_table'):
                struct = None
            return self._hideExcludedCols(struct,gridId)
        if table:
            tblobj = self.db.table(table)
            if source:
                handler = getattr(tblobj, 'baseView_%s' % source,None)
                columns = handler() if handler else source
            else:
                columns= tblobj.baseViewColumns()
            struct = self.newGridStruct(maintable=table)
            rows = struct.view().rows()
            rows.fields(columns)
        return self._hideExcludedCols(struct, gridId)

    def _hideExcludedCols(self, struct, gridId):
        gridNode=self.pageSource(gridId)
        excludeCols= gridNode.getAttr('excludeCols')
        if struct and excludeCols:
            excludeCols = excludeCols.split(',')
            for n in struct['#0.#0']:
                if n.getAttr('field') in excludeCols:
                    n.attr['hidden']=True
        return struct
        
    def rpc_getGridStruct(self,struct,table):
        """TODO
        
        :param struct: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :returns: TODO"""
        return self._prepareGridStruct(struct,table)
        
    @public_method
    def callTableMethod(self,table=None,methodname=None,**kwargs):
        """TODO
        
        ``callTableMethod()`` method is decorated with the :meth:`public_method
        s<gnr.core.gnrdecorator.public_method>` decorator
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param methodname: the method name of the :ref:`datarpc`"""
        handler = getattr(self.db.table(table), methodname, None)
        if not handler or not getattr(handler, 'is_rpc', False):
            handler = getattr(self.db.table(table),'rpc_%s' %methodname)
        return handler(**kwargs)
        
        
    def lazyBag(self, bag, name=None, location='page:resolvers'):
        """TODO
        
        :param bag: a :ref:`bag`
        :param name: TODO
        :param location: TODO"""
        freeze_path = self.site.getStaticPath(location, name, autocreate=-1)
        bag.makePicklable()
        bag.pickle('%s.pik' % freeze_path)
        return LazyBagResolver(resolverName=name, location=location, _page=self, sourceBag=bag)
        
    def log(self, msg,*args, **kwargs):
        mode = kwargs.pop('mode',None)
        mode = mode or 'log'
        self.clientPublish('gnrServerLog',msg=msg,args=args,kwargs=kwargs)
        print(f'pagename:{self.pagename}-:page_id:{self.page_id} >>\n{msg}',
                                    args,kwargs)

    ##### BEGIN: DEPRECATED METHODS ###
    @deprecated
    @property
    def config(self):
        return self.site.config
        
    ##### END: DEPRECATED METHODS #####

class LazyBagResolver(BagResolver):
    """TODO"""
    classKwargs = {'cacheTime': -1,
                   'readOnly': False,
                   'resolverName': None,
                   '_page': None,
                   'sourceBag': None,
                   'location': None,
                   'path': None,
                   'filter':None}
    classArgs = ['path']
        
    def load(self):
        """TODO"""
        if not self.sourceBag:
            self.getSource()
        sourceBag = self.sourceBag[self.path]
        if self.filter:
            
            flt,v=splitAndStrip(self.filter,'=',fixed=2)
            if  v:
                cb=lambda n: flt in n.attr and v in n.attr[flt]
            else:
                cb=lambda n: flt in n.label
            return sourceBag.filter(cb)
        result = Bag()
        for n in sourceBag:
            value = n.value
            if value and isinstance(value, Bag):
                path = n.label if not self.path else '%s.%s' % (self.path, n.label)
                value = LazyBagResolver(path=path, resolverName=self.resolverName, location=self.location)
            result.setItem(n.label.replace('.','_'), value, n.attr)
        return result
        
    def getSource(self):
        """TODO"""
        filepath = self._page.site.getStaticPath(self.location, self.resolverName)
        self.sourceBag = Bag('%s.pik' % filepath)

class GnrMakoPage(GnrWebPage):
    """TODO"""
    def onPreIniting(self, request_args, request_kwargs):
        """TODO"""
        request_kwargs['_plugin'] = 'mako'
        request_kwargs['mako_path'] = self.mako_template()
        
    def mako_template(self):
        """TODO"""
        pass
        
class GnrGenshiPage(GnrWebPage):
    """TODO"""
    def onPreIniting(self, request_args, request_kwargs):
        """TODO"""
        request_kwargs['_plugin'] = 'genshi'
        request_kwargs['genshi_path'] = self.genshi_template()
        
    def genshi_template(self):
        """TODO"""
        pass
        
class ClientDataChange(object):
    """TODO"""
    def __init__(self, path, value, attributes=None, reason=None, fired=False,
                 change_ts=None, change_idx=None, delete=False, **kwargs):
        self.path = path
        self.reason = reason
        self.value = value
        self.attributes = attributes
        self.fired = fired
        self.change_ts = change_ts or datetime.datetime.now()
        self.change_idx = change_idx
        self.delete = delete
        
    def __eq__(self, other):
        return self.path == other.path and self.reason == other.reason and self.fired == other.fired
        
    def update(self, other):
        """TODO
        
        :param other: TODO"""
        if hasattr(self.value, 'update') and hasattr(other.value, 'update'):
            self.value.update(other.value)
        else:
            self.value = other.value
        if other.attributes:
            self.attributes = self.attributes or dict()
            self.attributes.update(other.attributes)
            
    def __str__(self):
        return "Datachange path:%s, reason:%s, value:%s, attributes:%s" % (
        self.path, self.reason, self.value, self.attributes)
            
    def __repr__(self):
        return "Datachange path:%s, reason:%s, value:%s, attributes:%s" % (
        self.path, self.reason, self.value, self.attributes)
