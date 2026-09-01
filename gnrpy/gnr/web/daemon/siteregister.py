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
import Pyro4
import os
import re
from datetime import datetime
from collections import defaultdict

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage import ClientDataChange
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.web import logger

if hasattr(Pyro4.config, 'METADATA'):
    Pyro4.config.METADATA = False
if hasattr(Pyro4.config, 'REQUIRE_EXPOSE'):
    Pyro4.config.REQUIRE_EXPOSE = False

OLD_HMAC_MODE = hasattr(Pyro4.config, 'HMAC_KEY')
DAEMON_TIMEOUT_START = 5
DEFAULT_PAGE_MAX_AGE = 600
PROCESS_SELFDESTROY_TIMEOUT = 600

try:
    import pickle as pickle
except ImportError:
    import pickle

PYRO_HOST = 'localhost'
PYRO_PORT = 40004
PYRO_HMAC_KEY = 'supersecretkey'
PYRO_MULTIPLEX = True
LOCK_MAX_RETRY = 50
LOCK_EXPIRY_SECONDS = 10
RETRY_DELAY = 0.2
MAX_RETRY_ATTEMPTS = 4


class GnrDaemonException(Exception):
    pass


class GnrDaemonLocked(GnrDaemonException):
    pass


class BaseRemoteObject(object):
    def onSizeExceeded(self, msg_size, method, vargs, kwargs):
        logger.info('[%i-%i-%i %i:%i:%i]-----%s-----' % ((time.localtime()[:6]) + (self.__class__.__name__.upper(),)))
        logger.info('Message size:', msg_size)
        logger.info('Method :', method)
        logger.info('vargs, kwargs', vargs, kwargs)
        logger.info('**********')


#------------------------------- REMOTEBAG server SIDE ---------------------------
class RemoteStoreBagHandler(BaseRemoteObject):
    def __init__(self, siteregister):
        self.siteregister = siteregister

    def __getattr__(self, name):
        if name == '_pyroId':
            if '_pyroId' not in self.__dict__:
                raise AttributeError
            return self._pyroId

        def decore(*args, **kwargs):
            register_name = kwargs.pop('_siteregister_register_name', None)
            register_item_id = kwargs.pop('_siteregister_register_item_id', None)
            store = self.siteregister.get_item_data(register_item_id, register_name=register_name)
            if '_pyrosubbag' in kwargs:
                _pyrosubbag = kwargs.pop('_pyrosubbag')
                store = store.getItem(_pyrosubbag)
            h = getattr(store, name, None)
            if not h:
                raise AttributeError("PyroSubBag at %s has no attribute '%s'" % (_pyrosubbag, name))
            else:
                return h(*args, **kwargs)

        return decore


class BaseRegister(BaseRemoteObject):
    """docstring for BaseRegister"""
    def __init__(self, siteregister):
        self.siteregister = siteregister
        self.registerItems = dict()
        self.itemsData = dict()
        self.itemsTS = dict()
        self.locked_items = dict()
        self.cached_tables = defaultdict(dict)

    def lock_item(self, register_item_id, reason=None):
        locker = self.locked_items.get(register_item_id)
        if not locker:
            self.locked_items[register_item_id] = dict(reason=reason, count=1, last_lock_ts=datetime.now())
            return True
        elif locker['reason'] == reason:
            locker['count'] += 1
            locker['last_lock_ts'] = datetime.now()
            return True
        if (datetime.now() - locker['last_lock_ts']).total_seconds() > LOCK_EXPIRY_SECONDS:
            self.locked_items.pop(register_item_id, None)
        return False

    def unlock_item(self, register_item_id, reason=None):
        locker = self.locked_items.get(register_item_id)
        if locker:
            if locker['reason'] != reason:
                return False
            locker['count'] -= 1
            if not locker['count']:
                self.locked_items.pop(register_item_id, None)

    def addRegisterItem(self, register_item, data=None):
        register_item_id = register_item['register_item_id']
        self.registerItems[register_item_id] = register_item
        register_item['datachanges'] = list()
        register_item['datachanges_idx'] = 0
        register_item['subscribed_paths'] = set()
        data = Bag(data)
        data.subscribe('datachanges', any=lambda **kwargs: self._on_data_trigger(register_item=register_item, **kwargs))
        self.itemsData[register_item_id] = data

    def _on_data_trigger(self, node=None, ind=None, evt=None, pathlist=None, register_item=None, **kwargs):
        if evt == 'ins':
            pathlist.append(node.label)
        path = '.'.join(pathlist)
        if evt != 'del' and node.attr.get('_caching_table'):
            caching_subscribers = self.cached_tables[node.attr['_caching_table']]
            register_item_id = register_item['register_item_id']
            if register_item_id not in caching_subscribers:
                caching_subscribers[register_item_id] = set([path])
            else:
                caching_subscribers[register_item_id].add(path)
        for subscribed in register_item['subscribed_paths']:
            if path.startswith(subscribed):
                register_item['datachanges'].append(
                    ClientDataChange(path=path, value=node.value, reason='serverChange', attributes=node.attr))
                break

    def invalidateTableCache(self, table):
        table_cache = self.cached_tables.pop(table)
        for register_item_id, pathset in list(table_cache.items()):
            data = self.get_item_data(register_item_id)
            if not data:
                continue  # dead item
            for p in pathset:
                data[p] = None

    def getRemoteData(self, register_item_id):
        pass

    def updateTS(self, register_item_id):
        self.itemsTS[register_item_id] = datetime.now()

    def get_item_data(self, register_item_id):
        data = self.itemsData.get(register_item_id)
        if data is None:
            data = Bag()
        return data

    def get_item(self, register_item_id, include_data=False):
        item = self.registerItems.get(register_item_id)
        self.updateTS(register_item_id)
        if item and include_data:
            item['data'] = self.get_item_data(register_item_id)
        return item

    def exists(self, register_item_id):
        return register_item_id in self.registerItems

    def keys(self):
        return list(self.registerItems.keys())

    def items(self, include_data=None):
        if not include_data:
            return list(self.registerItems.items())
        return [(k, self.get_item(k, include_data=True)) for k in list(self.keys())]

    def values(self, include_data=False):
        if not include_data:
            return list(self.registerItems.values())
        return [self.get_item(k, include_data=True) for k in list(self.keys())]

    def refresh(self, register_item_id, last_user_ts=None, last_rpc_ts=None, refresh_ts=None):
        item = self.registerItems.get(register_item_id)
        if not item:
            return
        item['last_user_ts'] = max(item['last_user_ts'], last_user_ts) if item.get('last_user_ts') else last_user_ts
        item['last_rpc_ts'] = max(item['last_rpc_ts'], last_rpc_ts) if item.get('last_rpc_ts') else last_rpc_ts
        item['last_refresh_ts'] = max(item['last_refresh_ts'], refresh_ts) if item.get('last_refresh_ts') else refresh_ts
        return item

    @property
    def registerName(self):
        return self.__class__.__name__

    def drop_item(self, register_item_id):
        register_item = self.registerItems.pop(register_item_id, None)
        self.itemsData.pop(register_item_id, None)
        self.itemsTS.pop(register_item_id, None)
        return register_item

    def _live_children(self, keys, parent_register, link_name):
        """Pair each key with its item, pruning the keys that have none.

        A link set is a cache of what the children say about their parent: a key
        with no item is residual drift, not a reason to raise on every caller of
        the parent. Pruning here keeps the set converging instead of carrying a
        dead id for the life of the daemon.

        The parent is not passed in: dropRegisterLinks scans them, so one call
        cleans the key out of every parent that wrongly holds it, and a walk
        spanning several parents (a user's pages, across its connections) needs
        no special case. Pruning is the rare corrective path, so the scan costs
        nothing on the ordinary one.
        """
        for k in keys:
            register_item = self.registerItems.get(k)
            if register_item is None:
                self.siteregister.dropRegisterLinks(parent_register, link_name, k)
                continue
            yield k, register_item

    def update_item(self, register_item_id, upddict=None):
        register_item = self.get_item(register_item_id)
        if not register_item:
            return
        register_item.update(upddict)
        return register_item

    def get_datachanges(self, register_item_id, reset=False):
        register_item = self.get_item(register_item_id)
        if not register_item:
            return
        datachanges = register_item['datachanges']
        if reset:
            register_item['datachanges'] = []
            register_item['datachanges_idx'] = 0
        return datachanges

    def reset_datachanges(self, register_item_id):
        return self.update_item(register_item_id, dict(datachanges=list(), datachanges_idx=0))

    def set_datachange(self, register_item_id, path, value=None, attributes=None, fired=False, reason=None, replace=False, delete=False):
        register_item = self.get_item(register_item_id)
        if not register_item:
            return
        datachanges = register_item['datachanges']
        register_item['datachanges_idx'] = register_item.get('datachanges_idx', 0)
        register_item['datachanges_idx'] += 1
        datachange = ClientDataChange(path, value, attributes=attributes, fired=fired,
                                      reason=reason, change_idx=register_item['datachanges_idx'],
                                      delete=delete)
        if replace and datachange in datachanges:
            datachanges.pop(datachanges.index(datachange))
        datachanges.append(datachange)

    def drop_datachanges(self, register_item_id, path):
        register_item = self.get_item(register_item_id)
        if not register_item:
            return
        datachanges = register_item['datachanges']
        datachanges[:] = [dc for dc in datachanges if not dc.path.startswith(path)]

    def subscribe_path(self, register_item_id, path):
        register_item = self.get_item(register_item_id)
        register_item['subscribed_paths'].add(path)

    def get_dbenv(self, register_item_id):
        data = self.get_item_data(register_item_id)
        dbenvbag = data.getItem('dbenv') or Bag()
        dbenvbag.update((data.getItem('rootenv') or Bag()))

        def addToDbEnv(n, _pathlist=None):
            if n.attr.get('dbenv'):
                path = n.label if n.attr['dbenv'] is True else n.attr['dbenv']
                dbenvbag[path] = n.value

        _pathlist = []
        data.walk(addToDbEnv, _pathlist=_pathlist)
        return dbenvbag

    def dump(self, storagefile):
        pickle.dump(self.registerItems, storagefile)
        pickle.dump(self.itemsData, storagefile)
        pickle.dump(self.itemsTS, storagefile)
        pickle.dump(self.locked_items, storagefile)

    def load(self, storagefile):
        self.registerItems = pickle.load(storagefile)
        self.itemsData = pickle.load(storagefile)
        self.itemsTS = pickle.load(storagefile)
        self.locked_items = pickle.load(storagefile)


class GlobalRegister(BaseRegister):
    """docstring for GlobalRegister"""

    def __init__(self, *args, **kwargs):
        super(GlobalRegister, self).__init__(*args, **kwargs)
        self.create('*')

    def create(self, identifier=None):
        register_item = dict(
            start_ts=datetime.now(),
            register_item_id=identifier,
            register_name='global')
        self.addRegisterItem(register_item)
        return register_item

    def drop(self, identifier):
        self.drop_item(identifier)


class UserRegister(BaseRegister):
    """docstring for UserRegister"""
    def create(self, user, user_id=None, user_name=None, user_tags=None, avatar_extra=None):
        register_item = dict(
            register_item_id=user,
            start_ts=datetime.now(),
            user=user,
            user_id=user_id,
            user_name=user_name,
            user_tags=user_tags,
            avatar_extra=avatar_extra,
            connections=set(),
            register_name='user')
        self.addRegisterItem(register_item)
        return register_item

    def drop(self, user):
        self.siteregister.drop_connections(user)
        self.drop_item(user)


class ConnectionRegister(BaseRegister):
    """docstring for ConnectionRegister"""
    def create(self, connection_id, connection_name=None, user=None, user_id=None,
               user_name=None, user_tags=None, user_ip=None, user_agent=None, browser_name=None,
               electron_static=None):
        register_item = dict(
            register_item_id=connection_id,
            start_ts=datetime.now(),
            connection_name=connection_name,
            user=user,
            user_id=user_id,
            user_name=user_name,
            user_tags=user_tags,
            user_ip=user_ip,
            user_agent=user_agent,
            electron_static=electron_static,
            browser_name=browser_name,
            pages=set(),
            register_name='connection')
        self.addRegisterItem(register_item)
        return register_item

    def drop(self, register_item_id=None, cascade=None):
        self.siteregister.drop_pages(register_item_id)
        register_item = self.drop_item(register_item_id)
        if cascade:
            user = register_item['user']
            keys = self.user_connection_keys(user)
            if not keys:
                self.siteregister.drop_user(user)

    def user_connection_keys(self, user):
        # from the user item's link set; a list, so callers may drop while iterating
        user_item = self.siteregister.user_register.registerItems.get(user)
        if not user_item:
            return []
        return list(user_item['connections'])

    def user_connection_items(self, user):
        return [(k, register_item)
                for k, register_item in self._live_children(
                    self.user_connection_keys(user),
                    self.siteregister.user_register, 'connections')]

    def user_connections(self, user):
        return [register_item for k, register_item in self.user_connection_items(user)]


    def connections(self, user=None, include_data=None):
        if not user:
            return self.values(include_data=include_data)
        if include_data:
            # through user_connection_items so a dangling id is pruned here too:
            # get_item would return None for it and the caller would carry that
            # None instead of raising, which is the quieter of the two failures
            return [self.get_item(k, include_data=True)
                    for k, register_item in self.user_connection_items(user)]
        return self.user_connections(user)


class PageRegister(BaseRegister):
    def __init__(self, *args, **kwargs):
        super(PageRegister, self).__init__(*args, **kwargs)
        self.pageProfilers = dict()
        # Reverse index table -> set of page_id subscribed to it, so asking whether a
        # table is observed at all is a lookup instead of a scan of every registered
        # page. It duplicates the per-page ``subscribed_tables`` list, so every
        # mutation goes through updateSubscriptions and nowhere else: one place to
        # keep the two in step, instead of one per lifecycle event.
        self.tableSubscribers = defaultdict(set)

    def updateSubscriptions(self, page_id, subscribed_tables, add=None, remove=None):
        """The only writer of a page's subscriptions, list and index together.

        *subscribed_tables* is the page's own list, mutated in place. Pass *add* or
        *remove* to change one table, or neither to index the list as it stands (a
        page being created). Returns True when something changed.
        """
        if add is not None:
            if add in subscribed_tables:
                return False
            subscribed_tables.append(add)
            self.tableSubscribers[add].add(page_id)
            return True
        if remove is not None:
            if remove not in subscribed_tables:
                return False
            subscribed_tables.remove(remove)
            self._dropSubscriber(remove, page_id)
            return True
        for table in subscribed_tables:
            self.tableSubscribers[table].add(page_id)
        return bool(subscribed_tables)

    def dropSubscriptions(self, page_id, subscribed_tables=None):
        """Forget every subscription of a page that is going away.

        Driven by the index, not by the page's own list: the list says what the
        current item believes, the index says what notifyDbEvents will actually
        read. Scanning the index makes the removal atomic with the drop whatever
        happened to the item before (an overwritten registration, a restored
        pickle), so a dropped page can never leave a dangling subscriber behind.
        """
        for table in list(self.tableSubscribers):
            self._dropSubscriber(table, page_id)
        if subscribed_tables:
            del subscribed_tables[:]

    def _dropSubscriber(self, table, page_id):
        subscribers = self.tableSubscribers.get(table)
        if subscribers is None:
            return
        subscribers.discard(page_id)
        if not subscribers:
            del self.tableSubscribers[table]

    def subscribed_tables(self):
        """Tables with at least one subscribed page."""
        return list(self.tableSubscribers)

    def load(self, storagefile):
        # A restored pickle replaces registerItems wholesale: rebuild the index from
        # the restored per-page lists, or every restored subscription is invisible to
        # notifyDbEvents and whatever the index held before dangles.
        super(PageRegister, self).load(storagefile)
        self.tableSubscribers = defaultdict(set)
        for page_id, register_item in self.registerItems.items():
            for table in register_item.get('subscribed_tables') or []:
                self.tableSubscribers[table].add(page_id)

    def create(self, page_id, pagename=None, connection_id=None, subscribed_tables=None, user=None, user_ip=None, user_agent=None, relative_url=None, data=None):
        register_item_id = page_id
        start_ts = datetime.now()
        if register_item_id in self.registerItems:
            # Re-registering an existing page_id replaces the item wholesale: unindex
            # the previous life first, or its subscriptions dangle in the index and
            # outlive the item, breaking every notifyDbEvents on those tables.
            self.dropSubscriptions(register_item_id)
        if subscribed_tables:
            subscribed_tables = subscribed_tables.split(',')
        subscribed_tables = subscribed_tables or []
        self.updateSubscriptions(register_item_id, subscribed_tables)
        register_item = dict(
            register_item_id=register_item_id,
            pagename=pagename,
            connection_id=connection_id,
            start_ts=start_ts,
            subscribed_tables=subscribed_tables,
            user=user,
            user_ip=user_ip,
            user_agent=user_agent,
            relative_url=relative_url,
            datachanges=list(),
            subscribed_paths=set(),
            register_name='page')
        self.addRegisterItem(register_item, data=data)
        return register_item

    def drop(self, register_item_id=None, cascade=None):
        # Unindex before dropping the item: the index is read to reach the items, so
        # it must never point at one that is already gone.
        self.dropSubscriptions(register_item_id,
                               (self.registerItems.get(register_item_id) or {}
                                ).get('subscribed_tables'))
        register_item = self.drop_item(register_item_id)
        self.pageProfilers.pop(register_item_id, None)
        if cascade:
            connection_id = register_item['connection_id']
            n = self.connection_page_keys(connection_id)
            if not n:
                self.siteregister.drop_connection(connection_id)

    def filter_subscribed_tables(self, table_list):
        return [table for table in table_list if table in self.tableSubscribers]

    def subscribed_table_page_keys(self, table):
        return list(self.tableSubscribers.get(table, ()))

    def subscribed_table_page_items(self, table):
        # registerItems rather than get_item: the scan this replaces did not refresh
        # a page's timestamp, and notifying an event must not keep a page alive.
        items = []
        for k in self.subscribed_table_page_keys(table):
            register_item = self.registerItems.get(k)
            if register_item is None:
                # The index is a cache of the per-page lists: a key with no item is
                # residual drift, and raising here would abort the notification for
                # every live subscriber of the table. Prune it and move on.
                self._dropSubscriber(table, k)
                continue
            items.append((k, register_item))
        return items

    def subscribed_table_pages(self, table):
        return [register_item for k, register_item in self.subscribed_table_page_items(table)]

    def connection_page_keys(self, connection_id):
        # from the connection item's link set; a list, so callers may drop while iterating
        connection_item = self.siteregister.connection_register.registerItems.get(connection_id)
        if not connection_item:
            return []
        return list(connection_item['pages'])

    def connection_page_items(self, connection_id):
        return [(k, register_item)
                for k, register_item in self._live_children(
                    self.connection_page_keys(connection_id),
                    self.siteregister.connection_register, 'pages')]

    def connection_pages(self, connection_id):
        return [register_item
                for k, register_item in self.connection_page_items(connection_id)]

    def pages(self, connection_id=None, user=None, include_data=None, filters=None):
        # walk the link sets rather than the whole registry: a connection knows its
        # pages, a user knows its connections
        page_ids = None
        if connection_id:
            page_ids = self.connection_page_keys(connection_id)
        elif user:
            page_ids = [page_id
                        for cid in self.siteregister.user_connection_keys(user)
                        for page_id in self.connection_page_keys(cid)]
        if page_ids is None:
            pages = self.values(include_data=include_data)
        else:
            # same pruning as the per-parent readers: this one is on the request
            # path (validate_page_id falls back to it), and the include_data
            # branch is the quieter half — get_item returns None for a missing
            # key, so a dead id would travel on as a None into Bag(page)
            live = list(self._live_children(page_ids,
                                            self.siteregister.connection_register, 'pages'))
            if include_data:
                pages = [self.get_item(page_id, include_data=True) for page_id, _ in live]
            else:
                pages = [register_item for _, register_item in live]
        if connection_id and user:
            pages = [v for v in pages if v['user'] == user]
        if not filters or filters == '*':
            return pages
        fltdict = dict()
        for flt in filters.split(' AND '):
            fltname, fltvalue = flt.split(':', 1)
            fltdict[fltname] = fltvalue
        filtered = []

        def checkpage(page, fltname, fltval):
            value = page[fltname]
            if not value:
                return
            if not isinstance(value, (bytes, str)):
                return fltval == value
            try:
                return re.match(fltval, value)
            except Exception:
                return False

        for page in pages:
            page = Bag(page)
            for fltname, fltval in list(fltdict.items()):
                if checkpage(page, fltname, fltval):
                    filtered.append(page)
        return filtered

    def updatePageProfilers(self, page_id, pageProfilers):
        self.pageProfilers[page_id] = pageProfilers

    def setStoreSubscription(self, page_id, storename=None, client_path=None, active=None):
        register_item_data = self.get_item_data(page_id)
        subscription_path = '_subscriptions.%s' % storename
        storesub = register_item_data.getItem(subscription_path)
        if storesub is None:
            storesub = dict()
            register_item_data.setItem(subscription_path, storesub)
        pathsub = storesub.setdefault(client_path, {})
        pathsub['on'] = active

    def subscribeTable(self, page_id, table=None, subscribe=None, subscribeMode=None):
        register_item = self.get_item(page_id)
        subscribed_tables = register_item['subscribed_tables']
        if subscribe:
            self.updateSubscriptions(page_id, subscribed_tables, add=table)
        else:
            self.updateSubscriptions(page_id, subscribed_tables, remove=table)

    def notifyDbEvents(self, dbeventsDict=None, origin_page_id=None, dbevent_reason=None):
        for table, dbevents in list(dbeventsDict.items()):
            if not dbevents:
                continue
            table_code = table.replace('.', '_')
            self.siteregister.checkCachedTables(table)
            subscribers = self.subscribed_table_pages(table)
            if not subscribers:
                continue
            for page in subscribers:
                self.set_datachange(page['register_item_id'], 'gnr.dbchanges.%s' % table_code, dbevents,
                                    attributes=dict(from_page_id=origin_page_id, dbevent_reason=dbevent_reason))

    def setPendingContext(self, page_id, pendingContext):
        data = self.get_item_data(page_id)
        for serverpath, value, attr in pendingContext:
            data.setItem(serverpath, value, attr)
            if isinstance(value, Bag):
                data.clearBackRef()
                data.setBackRef()
            self.subscribe_path(page_id, serverpath)

    def setInClientData(self, path, value=None, attributes=None, page_id=None, filters=None,
                        fired=False, reason=None, public=False, replace=False):
        if filters:
            pages = [p['register_item_id'] for p in self.pages(filters=filters)]
        else:
            pages = [page_id]
        for page_id in pages:
            if isinstance(path, Bag):
                changeBag = path
                for changeNode in changeBag:
                    attr = changeNode.attr
                    self.set_datachange(page_id, path=attr.pop('_client_path'), value=changeNode.value,
                                        attributes=attr, fired=attr.pop('fired', None))
            else:
                self.set_datachange(page_id, path=path, value=value, reason=reason,
                                    attributes=attributes, fired=fired)


class SiteRegister(BaseRemoteObject):
    def __init__(self, server, sitename=None, storage_path=None):
        self.server = server
        self.global_register = GlobalRegister(self)
        self.page_register = PageRegister(self)
        self.connection_register = ConnectionRegister(self)
        self.user_register = UserRegister(self)
        self.remotebag_handler = RemoteStoreBagHandler(self)
        self.server.daemon.register(self.remotebag_handler, 'RemoteData')
        self.last_cleanup = 0
        self.sitename = sitename
        self.storage_path = storage_path
        self.catalog = GnrClassCatalog()
        self.allowed_users = None
        self.interproces_commands = dict()

    def on_reloader_restart(self):
        if self.server.gnr_daemon_uri:
            with Pyro4.Proxy(self.server.gnr_daemon_uri) as proxy:
                if not OLD_HMAC_MODE:
                    proxy._pyroHmacKey = self.server.hmac_key
                proxy.on_reloader_restart(sitename=self.sitename)

    def on_site_stop(self):
        logger.info('site %s stopped', self.sitename)

    def checkCachedTables(self, table):
        for register in (self.page_register, self.connection_register, self.user_register):
            if table in register.cached_tables:
                register.invalidateTableCache(table)

    def setConfiguration(self, cleanup=None):
        cleanup = cleanup or dict()
        self.page_max_age = int(cleanup.get('page_max_age') or DEFAULT_PAGE_MAX_AGE)
        self.guest_connection_max_age = int(cleanup.get('guest_connection_max_age') or 40)
        self.connection_max_age = int(cleanup.get('connection_max_age') or 7200)

    def updateRegisterLink(self, register, parent_id, link_name, child_id, add=None):
        """Add or drop *child_id* in a parent item's link set — the only writer of it.

        A parent/child link in the register lives in two places: the child item
        carries its parent id, the parent item carries the set of its children.
        Every change goes through here so the two cannot drift into phantom
        children or live children missing from the set.

        ``registerItems`` rather than ``get_item``: linking a child must not
        refresh the parent's timestamp, or a page being born would keep an
        otherwise idle connection alive. Returns True when the set changed.
        """
        if not parent_id:
            return False
        parent_item = register.registerItems.get(parent_id)
        if parent_item is None:
            return False
        children = parent_item.setdefault(link_name, set())
        if add:
            if child_id in children:
                return False
            children.add(child_id)
            return True
        if child_id not in children:
            return False
        children.discard(child_id)
        return True

    def dropRegisterLink(self, register, parent_id, link_name, child_id):
        """Discard *child_id* from one parent's link set, parent known.

        Unlike updateRegisterLink this does not require the child item to exist:
        it is what a pruning reader calls once it has found a key with no item.
        """
        parent_item = register.registerItems.get(parent_id)
        if parent_item is None:
            return False
        children = parent_item.get(link_name)
        if not children or child_id not in children:
            return False
        children.discard(child_id)
        return True

    def dropRegisterLinks(self, register, link_name, child_id):
        """Discard *child_id* from every parent that holds it, parent unknown.

        Driven by the link sets rather than by the child item, so the removal is
        atomic with the drop whatever happened to the child before. Reading the
        parent id off the child cannot do this: the child is exactly what may be
        missing, and skipping the unlink there is what leaves an id in a set for
        the life of the daemon.
        """
        dropped = False
        for parent_item in register.registerItems.values():
            children = parent_item.get(link_name)
            if children and child_id in children:
                children.discard(child_id)
                dropped = True
        return dropped

    def rebuildRegisterLinks(self, parent_register, child_register, parent_field, link_name):
        """Rebuild every parent's link set from the children that name it.

        Called after a register is restored from its pickle: the two registers are
        loaded independently, so the sets a parent carries know nothing of the
        children that actually came back.
        """
        for parent_item in parent_register.registerItems.values():
            parent_item[link_name] = set()
        for child_id, child_item in child_register.registerItems.items():
            parent_item = parent_register.registerItems.get(child_item.get(parent_field))
            if parent_item is not None:
                parent_item[link_name].add(child_id)

    def new_connection(self, connection_id, connection_name=None, user=None, user_id=None,
                       user_name=None, user_tags=None, user_ip=None, user_agent=None, browser_name=None,
                       avatar_extra=None, electron_static=None):
        assert not self.connection_register.exists(connection_id), \
            'SITEREGISTER ERROR: connection_id %s already registered' % connection_id
        if not self.user_register.exists(user):
            self.new_user(user, user_id=user_id, user_name=user_name, user_tags=user_tags, avatar_extra=avatar_extra)
        connection_item = self.connection_register.create(
            connection_id, connection_name=connection_name, user=user, user_id=user_id,
            user_name=user_name, user_tags=user_tags, user_ip=user_ip, user_agent=user_agent,
            browser_name=browser_name, electron_static=electron_static)
        self.updateRegisterLink(self.user_register, user, 'connections', connection_id, add=True)
        return connection_item

    def drop_pages(self, connection_id):
        for page_id in self.connection_page_keys(connection_id):
            self.drop_page(page_id)

    def drop_page(self, page_id, cascade=None):
        # driven by the sets, not by the page item: the item is exactly what may
        # already be gone, and that is when the unlink matters most
        self.dropRegisterLinks(self.connection_register, 'pages', page_id)
        return self.page_register.drop(page_id, cascade=cascade)

    def drop_connections(self, user):
        for connection_id in self.user_connection_keys(user):
            self.drop_connection(connection_id)

    def drop_connection(self, connection_id, cascade=None):
        # same as drop_page: a connection whose item vanished must still leave its
        # user's set, or drop_connections walks that id again on every call
        self.dropRegisterLinks(self.user_register, 'connections', connection_id)
        self.connection_register.drop(connection_id, cascade=cascade)

    def drop_user(self, user):
        self.user_register.drop(user)

    def user_connection_keys(self, user):
        return self.connection_register.user_connection_keys(user)

    def user_connection_items(self, user):
        return self.connection_register.user_connection_items(user)

    def user_connections(self, user):
        return self.connection_register.user_connections(user)

    def connection_page_keys(self, connection_id):
        return self.page_register.connection_page_keys(connection_id=connection_id)

    def connection_page_items(self, connection_id):
        return self.page_register.connection_page_items(connection_id=connection_id)

    def connection_pages(self, connection_id):
        return self.page_register.connection_pages(connection_id=connection_id)

    def new_page(self, page_id, pagename=None, connection_id=None, subscribed_tables=None, user=None,
                 user_ip=None, user_agent=None, relative_url=None, data=None):
        page_item = self.page_register.create(page_id, pagename=pagename, connection_id=connection_id,
                                              user=user, user_ip=user_ip, user_agent=user_agent,
                                              relative_url=relative_url, data=data)
        self.updateRegisterLink(self.connection_register, connection_id, 'pages', page_id, add=True)
        return page_item

    def new_user(self, user=None, user_tags=None, user_id=None, user_name=None, avatar_extra=None):
        user_item = self.user_register.create(user=user, user_tags=user_tags, user_id=user_id,
                                              user_name=user_name, avatar_extra=avatar_extra)
        return user_item

    def subscribed_table_pages(self, table=None):
        return self.page_register.subscribed_table_pages(table)

    def pages(self, connection_id=None, user=None, index_name=None, filters=None, include_data=None):
        if index_name:
            logger.info('call subscribed_table_pages instead of pages')
            return self.subscribed_table_pages(index_name)
        return self.page_register.pages(connection_id=connection_id, user=user, filters=filters,
                                        include_data=include_data)

    def page(self, page_id):
        return self.page_register.get_item(page_id)

    def connection(self, connection_id):
        return self.connection_register.get_item(connection_id)

    def user(self, user):
        return self.user_register.get_item(user)

    def counters(self):
        return {
            "users": len(self.users()),
            "connections": len(self.connections()),
            "pages": len(self.pages())
        }

    def users(self, include_data=None):
        return self.user_register.values(include_data)

    def connections(self, user=None, include_data=None):
        return self.connection_register.connections(user=user, include_data=include_data)

    def change_connection_user(self, connection_id, user=None, user_tags=None, user_id=None, user_name=None,
                               avatar_extra=None):
        connection_item = self.connection(connection_id)
        olduser = connection_item['user']
        newuser_item = self.user(user)
        if not newuser_item:
            newuser_item = self.new_user(user=user, user_tags=user_tags, user_id=user_id, user_name=user_name,
                                         avatar_extra=avatar_extra)
        connection_item['user'] = user
        connection_item['user_tags'] = user_tags
        connection_item['user_name'] = user_name
        connection_item['user_id'] = user_id
        connection_item['avatar_extra'] = avatar_extra
        # move the link before the drop_user guard below: it reads the old
        # user's link set, which must no longer hold this connection
        self.updateRegisterLink(self.user_register, olduser, 'connections', connection_id)
        self.updateRegisterLink(self.user_register, user, 'connections', connection_id, add=True)
        for p in self.pages(connection_id=connection_id):
            p['user'] = user
        if not self.connection_register.connections(olduser):
            self.drop_user(olduser)

    def refresh(self, page_id, last_user_ts=None, last_rpc_ts=None, pageProfilers=None):
        refresh_ts = datetime.now()
        page = self.page_register.refresh(page_id, last_user_ts=last_user_ts, last_rpc_ts=last_rpc_ts,
                                          refresh_ts=refresh_ts)
        if not page:
            return
        self.page_register.updatePageProfilers(page_id, pageProfilers)
        connection = self.connection_register.refresh(page['connection_id'], last_user_ts=last_user_ts,
                                                      last_rpc_ts=last_rpc_ts, refresh_ts=refresh_ts)
        if not connection:
            return
        return self.user_register.refresh(connection['user'], last_user_ts=last_user_ts,
                                          last_rpc_ts=last_rpc_ts, refresh_ts=refresh_ts)

    def claim_cleanup(self, min_gap_seconds):
        """Atomic check-and-set on last_cleanup. Returns True if the caller
        wins the right to run a cleanup pass; False if another caller has
        already claimed within the gap.

        ``last_cleanup`` is initialized to 0 in ``__init__``, so the very
        first caller after a daemon restart wins immediately regardless of
        wall-clock time (the previous lifetime's claim history is not
        carried over). Atomicity is guaranteed by the daemon's
        single-thread Pyro4 multiplex server: only one ``claim_cleanup``
        executes at a time across all concurrent callers."""
        now = time.time()
        if now - self.last_cleanup < min_gap_seconds:
            return False
        self.last_cleanup = now
        return True

    def expire_pages(self, connection_id):
        """Drop pages of `connection_id` idle longer than page_max_age
        (or guest_connection_max_age for guest users). Returns list of
        dropped page_ids."""
        now = datetime.now()
        dropped = []
        for page in self.page_register.pages(connection_id=connection_id):
            max_age = (self.guest_connection_max_age
                       if page['user'].startswith('guest_')
                       else self.page_max_age)
            last_refresh_ts = page.get('last_refresh_ts') or page.get('start_ts')
            if (now - last_refresh_ts).seconds > max_age:
                page_id = page['register_item_id']
                self.drop_page(page_id)
                dropped.append(page_id)
        return dropped

    def expire_connection(self, connection_id):
        """Drop the connection if idle longer than connection_max_age
        (or guest_connection_max_age for guest users). Returns True if
        dropped."""
        connection = self.connection_register.get_item(connection_id)
        if not connection:
            return False
        max_age = (self.guest_connection_max_age
                   if connection['user'].startswith('guest_')
                   else self.connection_max_age)
        last_refresh_ts = connection.get('last_refresh_ts') or connection.get('start_ts')
        if (datetime.now() - last_refresh_ts).seconds > max_age:
            self.drop_connection(connection_id, cascade=True)
            return True
        return False

    def get_register(self, register_name):
        return getattr(self, '%s_register' % register_name)

    def setStoreSubscription(self, page_id, storename=None, client_path=None, active=None):
        self.page_register.setStoreSubscription(page_id, storename=storename, client_path=client_path, active=active)

    def subscribeTable(self, page_id, table, subscribe, subscribeMode=None):
        self.page_register.subscribeTable(page_id, table=table, subscribe=subscribe, subscribeMode=subscribeMode)

    def subscription_storechanges(self, user, page_id):
        external_datachanges = self.page_register.get_datachanges(register_item_id=page_id, reset=True)
        page_item_data = self.page_register.get_item_data(page_id)
        if not page_item_data:
            return external_datachanges
        user_subscriptions = page_item_data.getItem('_subscriptions.user')
        if not user_subscriptions:
            return external_datachanges
        store_datachanges = []
        datachanges = self.user_register.get_datachanges(user)
        user_item_data = self.user_register.get_item_data(user)
        storesubscriptions_items = list(user_subscriptions.items())
        global_offsets = user_item_data.getItem('_subscriptions.offsets')
        if global_offsets is None:
            global_offsets = {}
            user_item_data.setItem('_subscriptions.offsets', global_offsets)
        for j, change in enumerate(datachanges):
            changepath = change.path
            change_idx = change.change_idx
            for subpath, subdict in storesubscriptions_items:
                if subdict['on'] and changepath.startswith(subpath):
                    if change_idx > subdict.get('offset', 0):
                        subdict['offset'] = change_idx
                        change.attributes = change.attributes or {}
                        if change_idx > global_offsets.get(subpath, 0):
                            global_offsets[subpath] = change_idx
                            change.attributes['_new_datachange'] = True
                        else:
                            change.attributes.pop('_new_datachange', None)
                        store_datachanges.append(change)
        return external_datachanges + store_datachanges

    def handle_ping(self, page_id=None, reason=None, _serverstore_changes=None, **kwargs):
        _children_pages_info = kwargs.get('_children_pages_info')
        _lastUserEventTs = kwargs.get('_lastUserEventTs')
        _lastRpc = kwargs.get('_lastRpc')
        _pageProfilers = kwargs.get('_pageProfilers')
        page_item = self.refresh(page_id, _lastUserEventTs, last_rpc_ts=_lastRpc, pageProfilers=_pageProfilers)
        if not page_item:
            return False
        catalog = self.catalog
        if _serverstore_changes:
            self.set_serverstore_changes(page_id, _serverstore_changes)
        if _children_pages_info:
            for k, v in list(_children_pages_info.items()):
                child_lastUserEventTs = v.pop('_lastUserEventTs', None)
                child_lastRpc = v.pop('_lastRpc', None)
                child_pageProfilers = v.pop('_pageProfilers', None)
                if v:
                    self.set_serverstore_changes(k, v)
                if child_lastUserEventTs:
                    child_lastUserEventTs = catalog.fromTypedText(child_lastUserEventTs)
                if child_lastRpc:
                    child_lastRpc = catalog.fromTypedText(child_lastRpc)
                self.refresh(k, child_lastUserEventTs, last_rpc_ts=child_lastRpc, pageProfilers=child_pageProfilers)
        envelope = Bag(dict(result=None))
        user = page_item['user']
        datachanges = self.handle_ping_get_datachanges(page_id, user=user)
        if datachanges:
            envelope.setItem('dataChanges', datachanges)
        if _children_pages_info:
            for k in list(_children_pages_info.keys()):
                datachanges = self.handle_ping_get_datachanges(k, user=user)
                if datachanges:
                    envelope.setItem('childDataChanges.%s' % k, datachanges)
        user_register_data = self.user_register.get_item_data(user)
        lastBatchUpdate = user_register_data.getItem('lastBatchUpdate')
        if lastBatchUpdate:
            if (datetime.now() - lastBatchUpdate).seconds < 5:
                envelope.setItem('runningBatch', True)
            else:
                user_register_data.setItem('lastBatchUpdate', None)
        return envelope

    def handle_ping_get_datachanges(self, page_id, user=None):
        result = Bag()
        store_datachanges = self.subscription_storechanges(user, page_id)
        if store_datachanges:
            for j, change in enumerate(store_datachanges):
                result.setItem('sc_%i' % j, change.value, change_path=change.path, change_reason=change.reason,
                               change_fired=change.fired, change_attr=change.attributes,
                               change_ts=change.change_ts, change_delete=change.delete)
        return result

    def set_serverstore_changes(self, page_id=None, datachanges=None):
        page_item_data = self.page_register.get_item_data(page_id)
        for k, v in list(datachanges.items()):
            page_item_data.setItem(k, self._parse_change_value(v))

    def _parse_change_value(self, change_value):
        if isinstance(change_value, (bytes, str)):
            try:
                v = self.catalog.fromTypedText(change_value)
                if isinstance(v, (bytes, str)) and hasattr(v, 'decode'):
                    v = v.decode('utf-8')
                return v
            except Exception as e:
                raise e
        return change_value

    def dump(self):
        """TODO"""
        with open(self.storage_path, 'wb') as storagefile:
            self.user_register.dump(storagefile)
            self.connection_register.dump(storagefile)
            self.page_register.dump(storagefile)

    def load(self):
        try:
            with open(self.storage_path) as storagefile:
                self.user_register.load(storagefile)
                self.connection_register.load(storagefile)
                self.page_register.load(storagefile)
            # The three registers are pickled and restored independently, so a
            # parent's link set knows nothing of the children that came back.
            # Rebuilt here rather than inside each load: it is the first point
            # where every item exists, and it keeps a child register from having
            # to reach up into the site to repair its parent.
            self.rebuildRegisterLinks(self.user_register, self.connection_register,
                                      'user', 'connections')
            self.rebuildRegisterLinks(self.connection_register, self.page_register,
                                      'connection_id', 'pages')
            loadedpath = self.storage_path.replace('.pik', '_loaded.pik')
            if os.path.exists(loadedpath):
                os.remove(loadedpath)
            os.rename(self.storage_path, loadedpath)
            return True
        except EOFError:
            return False

    def pendingProcessCommands(self):
        pid = os.getpid()
        if pid not in self.interproces_commands:
            self.interproces_commands[pid] = dict(commands=[])
        pidhandler = self.interproces_commands[pid]
        commands = pidhandler['commands']
        pidhandler['commands'] = []
        pidhandler['ts'] = datetime.now()
        return commands

    def sendProcessCommand(self, command, pid=None):
        if pid is None:
            pid = list(self.interproces_commands.keys())
        else:
            pid = [pid]
        now = datetime.now()
        for p in pid:
            pidhandler = self.interproces_commands[p]
            if (now - pidhandler['ts']).total_seconds() > PROCESS_SELFDESTROY_TIMEOUT:
                self.interproces_commands.pop(p)
            else:
                if isinstance(command, list):
                    pidhandler['commands'].extend(command)
                else:
                    pidhandler['commands'].append(command)

    def __getattr__(self, fname):
        if fname == '_pyroId':
            if '_pyroId' not in self.__dict__:
                raise AttributeError
            return self._pyroId

        def decore(*args, **kwargs):
            register_name = kwargs.pop('register_name', None)
            if not register_name:
                return self.__getattribute__(fname)(*args, **kwargs)
            register = self.get_register(register_name)
            h = getattr(register, fname)
            return h(*args, **kwargs)

        return decore


class GnrSiteRegisterServer(object):
    def __init__(self, sitename=None, daemon_uri=None, storage_path=None, debug=None):
        self.sitename = sitename
        self.gnr_daemon_uri = daemon_uri
        self.debug = debug
        self.storage_path = storage_path
        self._running = False

    def running(self):
        return self._running

    def run(self, autorestore=False):
        self._running = True
        if autorestore:
            self.siteregister.load()
        self.daemon.requestLoop(self.running)

    def stop(self, saveStatus=False):
        logger.info('stopping %s', saveStatus)
        if saveStatus:
            logger.info('SAVING STATUS', self.storage_path)
            self.siteregister.dump()
            logger.info('SAVED STATUS STATUS')
        self._running = False

    def start(self, port=None, host=None, socket=None, hmac_key=None, compression=None, multiplex=None,
              timeout=None, polltimeout=None, autorestore=False, run_now=True):
        if socket:
            pyrokw = dict(unixsocket=socket)
        else:
            pyrokw = dict(host=host)
            if port != '*':
                pyrokw['port'] = int(port or PYRO_PORT)
        Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
        self.hmac_key = hmac_key = (hmac_key or PYRO_HMAC_KEY)
        multiplex = multiplex or PYRO_MULTIPLEX
        if OLD_HMAC_MODE:
            Pyro4.config.HMAC_KEY = hmac_key
        if compression:
            Pyro4.config.COMPRESSION = True
        if multiplex:
            Pyro4.config.SERVERTYPE = "multiplex"
        if timeout:
            Pyro4.config.TIMEOUT = timeout
        if polltimeout:
            Pyro4.config.POLLTIMEOUT = timeout
        self.daemon = Pyro4.Daemon(**pyrokw)
        if not OLD_HMAC_MODE:
            self.daemon._pyroHmacKey = hmac_key
        self.siteregister = SiteRegister(self, sitename=self.sitename, storage_path=self.storage_path)
        autorestore = autorestore and os.path.exists(self.storage_path)
        self.main_uri = self.daemon.register(self, 'SiteRegisterServer')
        logger.info('autorestore %s for %s', autorestore, os.path.exists(self.storage_path))
        self.register_uri = self.daemon.register(self.siteregister, 'SiteRegister')
        logger.info("uri=%s", self.main_uri)
        if self.gnr_daemon_uri:
            with Pyro4.Proxy(self.gnr_daemon_uri) as proxy:
                if not OLD_HMAC_MODE:
                    proxy._pyroHmacKey = hmac_key
                proxy.onRegisterStart(self.sitename, server_uri=str(self.main_uri),
                                      register_uri=str(self.register_uri))
        if run_now:
            self.run(autorestore=autorestore)
