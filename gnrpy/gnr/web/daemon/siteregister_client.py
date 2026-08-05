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

import time
import _thread
import Pyro4
import os
from datetime import datetime

from gnr.core.gnrbag import Bag, BagResolver
from gnr.core.gnrconfig import gnrConfigPath
from gnr.web import logger

from gnr.web.daemon.siteregister import (
    GnrDaemonLocked,
    OLD_HMAC_MODE,
    DAEMON_TIMEOUT_START, MAX_RETRY_ATTEMPTS,
    LOCK_MAX_RETRY, RETRY_DELAY,
)

if hasattr(Pyro4.config, 'METADATA'):
    Pyro4.config.METADATA = False
if hasattr(Pyro4.config, 'REQUIRE_EXPOSE'):
    Pyro4.config.REQUIRE_EXPOSE = False

BAG_INSTANCE = Bag()


def remotebag_wrapper(func):
    def decore(self, *args, **kwargs):
        if self.rootpath:
            kwargs['_pyrosubbag'] = self.rootpath
        kwargs['_siteregister_register_name'] = self.register_name
        kwargs['_siteregister_register_item_id'] = self.register_item_id
        return func(self, *args, **kwargs)
    return decore


#------------------------------- REMOTEBAG CLIENT SIDE ---------------------------

class RemoteStoreBag(object):
    def __init__(self, uri=None, register_name=None, register_item_id=None, rootpath=None, hmac_key=None):
        self.register_name = register_name
        self.register_item_id = register_item_id
        self.rootpath = rootpath
        self.uri = uri
        self.proxy = Pyro4.Proxy(uri)
        self.hmac_key = hmac_key
        if not OLD_HMAC_MODE:
            self.proxy._pyroHmacKey = hmac_key

    def chunk(self, path):
        return RemoteStoreBag(uri=self.uri, register_name=self.register_name,
                              register_item_id=self.register_item_id, rootpath=self.rootpath,
                              hmac_key=self.hmac_key)

    @remotebag_wrapper
    def __str__(self, *args, **kwargs):
        with self.proxy as p:
            return p.asString(*args, **kwargs)

    @remotebag_wrapper
    def __getitem__(self, *args, **kwargs):
        with self.proxy as p:
            return p.__getitem__(*args, **kwargs)

    @remotebag_wrapper
    def __setitem__(self, *args, **kwargs):
        with self.proxy as p:
            return p.__setitem__(*args, **kwargs)

    @remotebag_wrapper
    def __len__(self, *args, **kwargs):
        with self.proxy as p:
            return p.__len__(*args, **kwargs)

    @remotebag_wrapper
    def __contains__(self, *args, **kwargs):
        with self.proxy as p:
            return p.__contains__(*args, **kwargs)

    @remotebag_wrapper
    def __eq__(self, *args, **kwargs):
        with self.proxy as p:
            return p.__eq__(*args, **kwargs)

    def __getattr__(self, name):
        with self.proxy as p:
            h = getattr(p, name)
            if not callable(h):
                return h

            def decore(*args, **kwargs):
                kwargs['_pyrosubbag'] = self.rootpath
                kwargs['_siteregister_register_name'] = self.register_name
                kwargs['_siteregister_register_item_id'] = self.register_item_id
                return h(*args, **kwargs)

            return decore


################################### CLIENT ##########################################

class SiteRegisterClient(object):
    STORAGE_PATH = 'siteregister_data.pik'

    def __init__(self, site):
        self.locked_exception = GnrDaemonLocked
        self.site = site
        self.siteregisterserver_uri = None
        self.siteregister_uri = None
        self.storage_path = os.path.join(self.site.site_path, self.STORAGE_PATH)
        self.errors = Pyro4.errors
        Pyro4.config.SERIALIZER = 'pickle'
        daemonconfig = self.site.config.getAttr('gnrdaemon')
        sitedaemonconfig = self.site.config.getAttr('sitedaemon') or {}
        sitedaemon_xml_path = os.path.join(self.site.site_path, 'sitedaemon.xml')
        if os.path.exists(sitedaemon_xml_path):
            from psutil import pid_exists
            sitedaemon_bag = Bag(sitedaemon_xml_path)
            params = sitedaemon_bag.getAttr('params')
            sitedaemon_pid = params.get('pid')
            if sitedaemon_pid and pid_exists(sitedaemon_pid):
                self.hmac_key = sitedaemonconfig.get('hmac_key') or daemonconfig['hmac_key']
                self.siteregisterserver_uri = params.get('main_uri')
                self.siteregister_uri = params.get('register_uri')
                logger.info(f"URIS: \nmain - {self.siteregisterserver_uri}\n{self.siteregister_uri}")
                sitedaemon_bag = None
                self.initSiteRegister()
                return
            else:
                logger.info('no sitedaemon process')
        if 'sockets' in daemonconfig:
            if daemonconfig['sockets'].lower() in ('t', 'true', 'y'):
                daemonconfig['sockets'] = os.path.join(gnrConfigPath(), 'sockets')
            if not os.path.isdir(daemonconfig['sockets']):
                os.makedirs(daemonconfig['sockets'])
            daemonconfig['socket'] = daemonconfig.get('socket') or os.path.join(daemonconfig['sockets'], 'gnrdaemon.sock')
        if daemonconfig.get('socket'):
            daemon_uri = 'PYRO:GnrDaemon@./u:%(socket)s' % daemonconfig
        else:
            daemon_uri = 'PYRO:GnrDaemon@%(host)s:%(port)s' % daemonconfig
        daemon_hmac = daemonconfig['hmac_key']
        if OLD_HMAC_MODE:
            Pyro4.config.HMAC_KEY = daemon_hmac
        self.gnrdaemon_proxy = Pyro4.Proxy(daemon_uri)
        self.hmac_key = daemon_hmac
        if not OLD_HMAC_MODE:
            self.gnrdaemon_proxy._pyroHmacKey = self.hmac_key

        with self.gnrdaemon_proxy as daemonProxy:
            if not self.runningDaemon(daemonProxy):
                raise Exception('GnrDaemon is not started')
            t_start = time.time()
            while not self.checkSiteRegisterServerUri(daemonProxy):
                if (time.time() - t_start) > DAEMON_TIMEOUT_START:
                    raise Exception('GnrDaemon timout')
        logger.debug(f'creating proxy {self.siteregister_uri} - {self.siteregisterserver_uri}')
        self.initSiteRegister()

    def initSiteRegister(self):
        self.siteregister = Pyro4.Proxy(self.siteregister_uri)
        if not OLD_HMAC_MODE:
            self.siteregister._pyroHmacKey = self.hmac_key
        self.remotebag_uri = self.siteregister_uri.replace(':SiteRegister@', ':RemoteData@')
        self.siteregister.setConfiguration(cleanup=self.site.custom_config.getAttr('cleanup'))

    def checkSiteRegisterServerUri(self, daemonProxy):
        if not self.siteregisterserver_uri:
            try:
                info = daemonProxy.getSite(self.site.currentDomainIdentifier, create=True,
                                           storage_path=self.storage_path, autorestore=True)
                self.siteregisterserver_uri = info.get('server_uri', False)
                if not self.siteregisterserver_uri:
                    time.sleep(1)
                else:
                    self.siteregister_uri = info['register_uri']
            except Exception as e:
                logger.warning(f'getSite failed for {self.site.currentDomainIdentifier}: {e}, retrying...')
                time.sleep(1)
        return self.siteregisterserver_uri

    def runningDaemon(self, daemonProxy):
        t_start = time.time()
        while (time.time() - t_start) < 2:
            try:
                daemonProxy.ping()
                return True
            except Pyro4.errors.CommunicationError:
                raise
        return False

    def pyroProxy(self, url):
        proxy = Pyro4.Proxy(url)
        if not OLD_HMAC_MODE:
            proxy._pyroHmacKey = self.hmac_key
        return proxy

    def new_page(self, page_id, page, data=None):
        register_item = self.siteregister.new_page(page_id, pagename=page.pagename,
                                                    connection_id=page.connection_id, user=page.user,
                                                    user_ip=page.user_ip, user_agent=page.user_agent,
                                                    relative_url=page.request.path_info, data=data)
        self.add_data_to_register_item(register_item)
        return register_item

    def new_connection(self, connection_id, connection):
        register_item = self.siteregister.new_connection(connection_id,
                                                          connection_name=connection.connection_name,
                                                          user=connection.user, user_id=connection.user_id,
                                                          user_tags=connection.user_tags, user_ip=connection.ip,
                                                          browser_name=connection.browser_name,
                                                          user_agent=connection.user_agent,
                                                          avatar_extra=connection.avatar_extra,
                                                          electron_static=connection.electron_static)
        self.add_data_to_register_item(register_item)
        return register_item

    def pages(self, connection_id=None, user=None, index_name=None, filters=None, include_data=None):
        lazy_data = include_data == 'lazy'
        if lazy_data:
            include_data = False
        pages = self.siteregister.pages(connection_id=connection_id, user=user, index_name=index_name,
                                        filters=filters, include_data=include_data)
        return self.adaptListToDict(pages, lazy_data=lazy_data)

    def connections(self, user=None, include_data=None):
        lazy_data = include_data == 'lazy'
        if lazy_data:
            include_data = False
        connections = self.siteregister.connections(user=user, include_data=include_data)
        return self.adaptListToDict(connections, lazy_data=lazy_data)

    def adaptListToDict(self, l, lazy_data=None):
        return dict([(c['register_item_id'], self.add_data_to_register_item(c) if lazy_data else c) for c in l])

    def counters(self):
        return {
            "users": len(self.users()),
            "connections": len(self.connections()),
            "pages": len(self.pages())
        }

    def users(self, include_data=None):
        lazy_data = include_data == 'lazy'
        if lazy_data:
            include_data = False
        users = self.siteregister.users(include_data=include_data)
        return self.adaptListToDict(users, lazy_data=lazy_data)

    def refresh(self, page_id, ts=None, lastRpc=None, pageProfilers=None):
        return self.siteregister.refresh(page_id, last_user_ts=ts, last_rpc_ts=lastRpc, pageProfilers=pageProfilers)

    def connectionStore(self, connection_id, triggered=False):
        return self.make_store('connection', connection_id, triggered=triggered)

    def userStore(self, user, triggered=False):
        return self.make_store('user', user, triggered=triggered)

    def pageStore(self, page_id, triggered=False):
        return self.make_store('page', page_id, triggered=triggered)

    def globalStore(self, triggered=False):
        return self.make_store('global', '*', triggered=triggered)

    def make_store(self, register_name, register_item_id, triggered=None):
        return ServerStore(self, register_name, register_item_id=register_item_id, triggered=triggered)

    def get_item(self, register_item_id, include_data=False, register_name=None):
        lazy_data = include_data == 'lazy'
        if include_data == 'lazy':
            include_data = False
        register_item = self.siteregister.get_item(register_item_id, include_data=include_data,
                                                    register_name=register_name)
        if register_item and lazy_data:
            self.add_data_to_register_item(register_item)
        return register_item

    def add_data_to_register_item(self, register_item):
        register_item['data'] = RemoteStoreBag(self.remotebag_uri, register_item['register_name'],
                                               register_item['register_item_id'], hmac_key=self.hmac_key)
        return register_item

    def page(self, page_id, include_data=None):
        return self.get_item(page_id, include_data=include_data, register_name='page')

    def connection(self, connection_id, include_data=None):
        return self.get_item(connection_id, include_data=include_data, register_name='connection')

    def user(self, user, include_data=None):
        return self.get_item(user, include_data=include_data, register_name='user')

    def _debug(self, mode, name, *args, **kwargs):
        logger.debug('external_%s' % mode, name, 'ARGS', args, 'KWARGS', kwargs)

    def dump(self):
        """TODO"""
        self.siteregister.dump()
        logger.debug('DUMP REGISTER %s' % self.site.site_name)

    def load(self):
        result = self.siteregister.load()
        if result:
            logger.info('SITEREGISTER %s LOADED' % self.site.site_name)
        else:
            logger.info('UNABLE TO LOAD REGISTER %s' % self.site.site_name)

    def __getattr__(self, name):
        h = getattr(self.siteregister, name)
        if not callable(h):
            return h

        def decore(*args, **kwargs):
            attempt = 0
            r = None
            while attempt < MAX_RETRY_ATTEMPTS:
                try:
                    r = h(*args, **kwargs)
                    break
                except Exception:
                    attempt += 1
            return r

        return decore


##############################################################################

class ServerStore(object):
    def __init__(self, parent, register_name=None, register_item_id=None, triggered=True, max_retry=None, retry_delay=None):
        self.siteregister = parent
        self.register_name = register_name
        self.register_item_id = register_item_id
        self.triggered = triggered
        self.max_retry = max_retry or LOCK_MAX_RETRY
        self.retry_delay = retry_delay or RETRY_DELAY
        self._register_item = '*'
        self.thread_id = _thread.get_ident()

    def __enter__(self):
        k = 0
        self.start_locking_time = time.time()
        while not self.siteregister.lock_item(self.register_item_id, reason=self.thread_id,
                                               register_name=self.register_name):
            time.sleep(self.retry_delay)
            k += 1
            if k > self.max_retry:
                logger.error("Unable to lock store: %s item %s", self.register_name, self.register_item_id)
                raise GnrDaemonLocked()
        self.success_locking_time = time.time()
        return self

    def __exit__(self, type, value, tb):
        self.siteregister.unlock_item(self.register_item_id, reason=self.thread_id,
                                       register_name=self.register_name)

    def reset_datachanges(self):
        return self.siteregister.reset_datachanges(self.register_item_id, register_name=self.register_name)

    def set_datachange(self, path, value=None, attributes=None, fired=False, reason=None, replace=False, delete=False):
        return self.siteregister.set_datachange(self.register_item_id, path, value=value, attributes=attributes,
                                                 fired=fired, reason=reason, replace=replace, delete=delete,
                                                 register_name=self.register_name)

    def drop_datachanges(self, path):
        self.siteregister.drop_datachanges(self.register_item_id, path, register_name=self.register_name)

    def subscribe_path(self, path):
        self.siteregister.subscribe_path(self.register_item_id, path, register_name=self.register_name)

    @property
    def register_item(self):
        return self.siteregister.get_item(self.register_item_id, include_data='lazy',
                                          register_name=self.register_name)

    @property
    def data(self):
        if self.register_item:
            return self.register_item['data']

    @property
    def datachanges(self):
        return self.register_item['datachanges']

    @property
    def subscribed_paths(self):
        return self.register_item['subscribed_paths']

    def __getattr__(self, fname):
        if hasattr(BAG_INSTANCE, fname):
            def decore(*args, **kwargs):
                data = self.data
                if data is not None:
                    return getattr(data, fname)(*args, **kwargs)
            return decore
        else:
            raise AttributeError("register_item has no attribute '%s'" % fname)


#################################### UTILS ####################################################################

class RegisterResolver(BagResolver):
    classKwargs = {'cacheTime': 1,
                   'readOnly': False,
                   'user': None,
                   'connection_id': None,
                   '_page': None
                   }
    classArgs = ['user']

    def load(self):
        if not self.user:
            return self.list_users()
        elif not self.connection_id:
            return self.list_connections(user=self.user)
        else:
            return self.list_pages(connection_id=self.connection_id)

    @property
    def register(self):
        return self._page.site.register

    def list_users(self):
        usersDict = self.register.users(include_data=True)
        result = Bag()
        for user, item_user in list(usersDict.items()):
            item = Bag()
            data = item_user.pop('data', None)
            item_user.pop('datachanges', None)
            item_user.pop('datachanges_idx', None)
            item['info'] = Bag(item_user)
            item['data'] = data
            item.setItem('connections', RegisterResolver(user=user), cacheTime=3)
            result.setItem(user, item, user=user)
        return result

    def list_connections(self, user):
        connectionsDict = self.register.connections(user=user, include_data=True)
        result = Bag()
        for connection_id, connection in list(connectionsDict.items()):
            delta = (datetime.now() - connection['start_ts']).seconds
            user = connection['user'] or 'Anonymous'
            connection_name = connection['connection_name']
            itemlabel = '%s (%i)' % (connection_name, delta)
            item = Bag()
            data = connection.pop('data', None)
            item['info'] = Bag(connection)
            item['data'] = data
            item.setItem('pages', RegisterResolver(user=user, connection_id=connection_id), cacheTime=2)
            result.setItem(itemlabel, item, user=user, connection_id=connection_id)
        return result

    def list_pages(self, connection_id):
        pagesDict = self.register.pages(connection_id=connection_id, include_data=True)
        result = Bag()
        for page_id, page in list(pagesDict.items()):
            delta = (datetime.now() - page['start_ts']).seconds
            pagename = page['pagename'].replace('.py', '')
            itemlabel = '%s (%i)' % (pagename, delta)
            item = Bag()
            data = page.pop('data', None)
            item['info'] = Bag(page)
            item['data'] = data
            result.setItem(itemlabel, item, user=item['user'], connection_id=item['connection_id'], page_id=page_id)
        return result

    def resolverSerialize(self):
        attr = super(RegisterResolver, self).resolverSerialize()
        attr['kwargs'].pop('_page', None)
        return attr
