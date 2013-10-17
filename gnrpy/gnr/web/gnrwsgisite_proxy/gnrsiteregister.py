#-*- coding: UTF-8 -*-  
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

import Pyro4
from datetime import datetime
from gnr.core.gnrbag import Bag
import re

PYRO_HOST = 'localhost'
PYRO_PORT = 40004
PYRO_HMAC_KEY = 'supersecretkey'

class BaseRegister(object):
    """docstring for BaseRegister"""
    def __init__(self, siteregister):
        self.siteregister = siteregister
        self.registerItems = dict() 
        self.itemsData = dict()
        self.itemsTS = dict()

    def addRegisterItem(self,register_item):
        self.registerItems[register_item['register_item_id']] = register_item

    def attachData(self,register_item_id,data):
        self.itemsData[register_item_id] = Bag(data)
        self.refresh(register_item_id)

    def refresh(self,register_item_id):
        self.itemsTS[register_item_id] = datetime.now()

    def getData(self,register_item_id):
        return self.itemsData[register_item_id]

    def exists(self,register_item_id):
        return register_item_id in self.registerItems

    def keys(self):
        return self.registerItems.keys()

    def items(self):
        return self.registerItems.items()

    def values(self):
        return self.registerItems.values()

    def dropItem(self,register_item_id):
        register_item = self.registerItems.pop(register_item_id,None)
        self.itemsData.pop(register_item_id,None)
        self.itemsTS.pop(register_item_id,None)
        return register_item





class UserRegister(BaseRegister):
    """docstring for UserRegister"""
    def create(self, user, connection_item):
        register_item = dict(
                register_item_id=user,
                start_ts=datetime.now(),
                _new=True,
                user=user,
                user_id=connection_item['user_id'],
                user_name=connection_item['user_name'],
                user_tags=connection_item['user_tags'],
                avatar_extra=connection_item.get('avatar_extra'),
                connections={}
                )
        self.addRegisterItem(register_item)
        return register_item

class ConnectionRegister(BaseRegister):
    """docstring for ConnectionRegister"""
    def create(self, connection_id, connection_name=None,user=None,user_id=None,
                            user_name=None,user_tags=None,user_ip=None,user_agent=None,browser_name=None):
        register_item = dict(
                register_item_id=connection_id,
                start_ts=datetime.now(),
                connection_name = connection_name,
                user= user, 
                user_id= user_id,
                user_name = user_name,
                user_tags = user_tags,
                user_ip=user_ip,
                user_agent=user_agent,
                browser_name=browser_name)

        self.addRegisterItem(register_item)
        return register_item

    def drop(self,register_item_id=None,cascade=None):
        register_item = self.dropItem(register_item_id)
        if cascade:
            user = register_item['user']
            keys = self.user_connection_keys(user)
            if not keys:
                self.siteregister.drop_user(user)

    def user_connection_keys(self,user):
        return [k for k,v in self.items() if v['user'] == user]

    def user_connection_items(self,user):
        return [(k,v) for k,v in self.items() if v['user'] == user]

    def user_connections(self,user):
        return [v for k,v in self.items() if v['user'] == user]

class PageRegister(BaseRegister):
    """docstring for PageRegister"""
    def create(self, page_id,pagename=None,connection_id=None,subscribed_tables=None,user=None,user_ip=None,user_agent=None ,data=None):
        register_item_id = page_id
        start_ts = datetime.now()
        if subscribed_tables:
            subscribed_tables = subscribed_tables.split(',')
        register_item = dict(
                register_item_id=register_item_id,
                pagename=pagename,
                connection_id=connection_id,
                start_ts=start_ts,
                subscribed_tables=subscribed_tables or [],
                user=user,
                user_ip=user_ip,
                user_agent=user_agent,
                datachanges=list(),
                subscribed_paths=set()
                )
        if data:
            self.attachData(register_item_id,data)
            #register_item['data'] = Bag(data)

        self.addRegisterItem(register_item)
        return register_item


    def drop(self,register_item_id=None,cascade=None):
        register_item = self.dropItem(register_item_id)
        if cascade:
            connection_id = register_item['connection_id']
            n = self.siteregister.connectionPagesKeys(connection_id)
            if not n:
                self.siteregister.drop_connection(connection_id)


    def subscribed_table_page_keys(self,table):
        return [k for k,v in self.items() if table in v['subscribed_tables']]

    def subscribed_table_page_items(self,table):
        return [(k,v) for k,v in self.items() if table in v['subscribed_tables']]

    def subscribed_table_pages(self,table):
        return [v for k,v in self.items() if table in v['subscribed_tables']]



    def connection_page_keys(self,connection_id):
        return [k for k,v in self.items() if v['connection_id'] == connection_id]

    def connection_page_items(self,connection_id):
        return [(k,v) for k,v in self.items() if v['connection_id'] == connection_id]

    def connection_pages(self,connection_id):
        return [v for k,v in self.items() if v['connection_id'] == connection_id]

class SiteRegister(object):
    def __init__(self,site):
        self.site = site
        self.p_register = PageRegister(self)
        self.c_register = ConnectionRegister(self)
        self.u_register = UserRegister(self)

    def new_connection(self,connection_id,connection_name=None,user=None,user_id=None,
                            user_name=None,user_tags=None,user_ip=None,user_agent=None,browser_name=None):
        assert not self.c_register.exists(connection_id), 'SITEREGISTER ERROR: connection_id %s already registered' % connection_id
        connection_item = self.c_register.create(connection_id, connection_name=connection_name,user=user,user_id=user_id,
                            user_name=user_name,user_tags=user_tags,user_ip=user_ip,user_agent=user_agent,browser_name=browser_name)
        return connection_item


    def drop_page(self,page_id, cascade=None):
        return self.p_register.drop(page_id,cascade=cascade)   

    def drop_connection(self,connection_id,cascade=None):
        self.c_register.drop(connection_id,cascade=cascade)

    def drop_user(self,user):
        self.u_register.drop(user)

    def user_connection_keys(self,user):
        self.c_register.user_connection_keys(user)

    def user_connection_items(self,user):
        self.c_register.user_connection_items(user)

    def user_connections(self,user):
        self.c_register.user_connections(user)

    def connection_page_keys(self,connection_id):
        self.p_register.connection_page_keys(connection_id=connection_id)

    def connection_page_items(self,connection_id):
        self.p_register.connection_page_items(connection_id=connection_id)

    def connection_pages(self,connection_id):
        self.p_register.connection_pages(connection_id=connection_id)


    def new_page(self,page_id,pagename=None,connection_id=None,subscribed_tables=None,user=None,user_ip=None,user_agent=None ,data=None):
        page_item = self.p_register.create(page_id, pagename = pagename,connection_id=connection_id,user=user,
                                            user_id=user_ip,user_agent=user_agent, data=data)
        return page_item




    def pages(self, connection_id=None, filters=None):
        pages = self.p_register.values()

        if not filters or filters == '*':
            return pages

        fltdict = dict()
        for flt in filters.split(' AND '):
            fltname, fltvalue = flt.split(':', 1)
            fltdict[fltname] = fltvalue
        filtered = dict()

        def checkpage(page, fltname, fltval):
            value = page[fltname]
            if not value:
                return
            if not isinstance(value, basestring):
                return fltval == value
            try:
                return re.match(fltval, value)
            except:
                return False

        for page_id, page in pages.items():
            page = Bag(page)
            for fltname, fltval in fltdict.items():
                if checkpage(page, fltname, fltval):
                    filtered[page_id] = page
        return filtered



    ###################################### TO DO ######################################

    def refresh(self,*args,**kwargs):
        return self.siteregister.refresh(*args,**kwargs)

    def cleanup(self,*args,**kwargs):
        return self.siteregister.cleanup(*args,**kwargs)

    def connection(self,*args,**kwargs):
        return self.siteregister.connection(*args,**kwargs)




    



    def page(self,*args,**kwargs):
        return self.siteregister.page(*args,**kwargs)   

    def change_connection_user(self,*args,**kwargs):
        return self.siteregister.change_connection_user(*args,**kwargs)    

    def users(self,*args,**kwargs):
        return self.siteregister.users(*args,**kwargs)   





    def debug(self,mode,name,*args,**kwargs):
        if not name in self.current:
            print 'external_%s' %mode,name,'ARGS',args,'KWARGS',kwargs
            self.current[name] = True

    def __getattr__(self,name):
        h = getattr(self.siteregister,name)
        if not callable(h):
            self.debug('property',name)
            return h
        def decore(*args,**kwargs):
            self.debug('callable',name,*args,**kwargs)
            return h(*args,**kwargs)
        return decore




################################### CLIENT ##########################################

class SiteRegisterClient(object):
 

    def __init__(self,site,host=None,port=None,hmac_key=None):
        self.site = site
        host = host or PYRO_HOST
        port = port or PYRO_PORT
        hmac_key = str(hmac_key or PYRO_HMAC_KEY)
        Pyro4.config.HMAC_KEY = hmac_key
        Pyro4.config.SERIALIZER = 'pickle'
        uri = 'PYRO:SiteRegister@%s:%i' %(host,int(port))
        print 'URI',uri
        self.siteregister =  Pyro4.Proxy(uri)

        #self.siteregister = SiteRegister(site)

    def pages(self,*args,**kwargs):
        return self.siteregister.pages(*args,**kwargs)

    def refresh(self,*args,**kwargs):
        return self.siteregister.refresh(*args,**kwargs)

    def cleanup(self,*args,**kwargs):
        return self.siteregister.cleanup(*args,**kwargs)

    def connection(self,*args,**kwargs):
        return self.siteregister.connection(*args,**kwargs)



    def new_page(self, page_id, page, data=None):
        return self.siteregister.new_page( page_id, pagename = page.pagename,connection_id=page.connection_id,user=page.user,
                                            user_id=page.user_ip,user_agent=page.user_agent, data=data)


    def new_connection(self, connection_id, connection):
        return self.siteregister.new_connection(connection_id,connection_name = connection.connection_name,user=connection.user,
                                                    user_id=connection.user_id,user_tags=connection.user_tags,ip=connection.ip,browser_name=connection.browser_name,
                                                    user_agent=connection.user_agent)


    def page(self,*args,**kwargs):
        return self.siteregister.page(*args,**kwargs)

    def change_connection_user(self,*args,**kwargs):
        return self.siteregister.change_connection_user(*args,**kwargs)    

    def users(self,*args,**kwargs):
        return self.siteregister.users(*args,**kwargs)   

    def drop_page(self,*args,**kwargs):
        return self.siteregister.drop_page(*args,**kwargs)   

    def _debug(self,mode,name,*args,**kwargs):
        print 'external_%s' %mode,name,'ARGS',args,'KWARGS',kwargs




    def connectionStore(self,*args,**kwargs):
        return self.siteregister.connectionStore(*args,**kwargs)
        
    def pageStore(self,*args,**kwargs):
        return self.siteregister.pageStore(*args,**kwargs)        

    def userStore(self,*args,**kwargs):
        return self.siteregister.userStore(*args,**kwargs)    



    def __getattr__(self,name):
        h = getattr(self.siteregister,name)
        if not callable(h):
            self._debug('property',name)
            return h
        def decore(*args,**kwargs):
            self._debug('callable',name,*args,**kwargs)
            return h(*args,**kwargs)
        return decore








