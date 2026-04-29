# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrasync_aio : asyncio/aiohttp port of gnrasync.py (legacy Tornado)
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

import asyncio
import functools
import inspect
import os
import signal
import ssl as ssl_module
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import wraps

from aiohttp import WSMsgType, web

from gnr.core.gnrbag import Bag, TraceBackResolver
from gnr.core.gnrstring import fromJson
from gnr.web import logger
from gnr.web.gnrwsgisite import GnrWsgiSite
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import (
    AsyncWebSocketHandler as _LegacyAsyncWebSocketHandler,
)

MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3


def threadpool(func):
    """Marker decorator: handler runs in the threadpool executor."""
    func._executor = 'threadpool'
    return func


def lockedCoroutine(f):
    """Async lock decorator. Equivalent of legacy @gen.coroutine + lock.acquire."""
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            result = f(self, *args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
    return wrapper


def lockedThreadpool(f):
    """Async lock + threadpool execution. Equivalent of legacy @gen.coroutine
    + lock.acquire + executor.submit."""
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        async with self.lock:
            loop = asyncio.get_running_loop()
            executor = self.server.executors['threadpool']
            await loop.run_in_executor(
                executor,
                functools.partial(f, self, *args, **kwargs),
            )
    return wrapper


class DelayedCall:
    """Replacement for the Tornado-based DelayedCall.

    Uses asyncio.get_running_loop().call_later, which returns a TimerHandle
    with .cancel() — no need to keep a separate remove_timeout call.
    """

    def __init__(self, server, delay, cb, *args, **kwargs):
        loop = asyncio.get_running_loop()
        self.server = server
        self.handle = loop.call_later(delay, functools.partial(cb, *args, **kwargs))

    def cancel(self):
        self.handle.cancel()


class SharedObject:
    """In-memory shared state with optional persistence and pub/sub broadcast.

    Concurrency model: a per-instance asyncio.Lock guards write operations
    (datachange, save, load) and serializes them. Mutations on the inner
    Bag are signalled via _on_data_trigger (sync callback from gnrbag), which
    schedules an async broadcast to all subscribers using create_task.
    """

    default_savedir = 'site:async/sharedobjects'

    def __init__(self, manager, shared_id, expire=None, startData=None,
                 read_tags=None, write_tags=None, filepath=None,
                 dbSaveKw=None, saveInterval=None, autoSave=None,
                 autoLoad=None, **kwargs):
        self.manager = manager
        self.lock = asyncio.Lock()
        self.server = manager.server
        self.shared_id = shared_id
        self._data = Bag(dict(root=Bag(startData)))
        self.read_tags = read_tags
        self.write_tags = write_tags
        self._data.subscribe('datachanges', any=self._on_data_trigger)
        self.subscribed_pages = dict()
        self.expire = expire or 0
        self.focusedPaths = {}
        if self.expire < 0:
            self.expire = 365 * 24 * 60 * 60
        self.timeout = None
        self.autoSave = autoSave
        self.saveInterval = saveInterval
        self.autoLoad = autoLoad
        self.changes = False
        self.dbSaveKw = dbSaveKw
        self.onInit(**kwargs)

    @property
    def savepath(self):
        return self.server.gnrsite.storageNode(self.default_savedir, '%s.xml' % self.shared_id)

    @property
    def data(self):
        return self._data['root']

    @property
    def sql_data_column(self):
        return self.dbSaveKw.get('data_column') or 'shared_data'

    @property
    def sql_backup_column(self):
        return self.dbSaveKw.get('backup_column') or 'shared_backup'

    @lockedThreadpool
    def save(self):
        if self.changes:
            if self.dbSaveKw:
                kw = dict(self.dbSaveKw)
                tblobj = self.server.db.table(kw.pop('table'))
                handler = getattr(tblobj, 'saveSharedObject', None)
                if handler:
                    handler(self.shared_id, self.data, **kw)
                else:
                    self.sql_save(tblobj)
                self.server.db.commit()
            else:
                with self.savepath.open(mode='wb') as savefile:
                    self.data.toXml(savefile, unresolved=True, autocreate=True)
        self.changes = False

    @lockedThreadpool
    def load(self):
        if self.dbSaveKw:
            tblobj = self.server.db.table(self.dbSaveKw['table'])
            handler = getattr(tblobj, 'loadSharedObject', None)
            if handler:
                data = handler(self.shared_id)
            else:
                data = self.sql_load(tblobj)
        elif self.savepath.exists:
            with self.savepath.open(mode='r') as savefile:
                data = Bag(savefile)
        else:
            data = Bag()
        self._data['root'] = data
        self.changes = False

    def sql_save(self, tblobj):
        backup = self.dbSaveKw.get('backup')
        data_column = self.sql_data_column
        with tblobj.recordToUpdate(self.shared_id) as record:
            if not self.data:
                logger.error('NO DATA IN SAVING: %s', self.shared_id)
            record[data_column] = deepcopy(self.data)
            onSavingHandler = getattr(tblobj, 'shared_onSaving', None)
            if onSavingHandler:
                onSavingHandler(record)
            if backup:
                backup_column = self.sql_backup_column
                if not record[backup_column]:
                    record[backup_column] = Bag()
                    n = 0
                else:
                    n = int(list(record[backup_column].keys())[-1].split('_')[1]) + 1
                record[backup_column].setItem('v_%s' % n, record[data_column], ts=datetime.now())
                if len(record[backup_column]) > backup:
                    record[backup_column].popNode('#0')

    def sql_load(self, tblobj, version=None):
        record = tblobj.record(self.shared_id).output('bag')
        onLoadingHandler = getattr(tblobj, 'shared_onLoading', None)
        if onLoadingHandler:
            onLoadingHandler(record)
        if not version:
            return record[self.sql_data_column]
        return record[self.sql_backup_column].getItem('v_%i' % version)

    def onInit(self, **kwargs):
        if self.autoLoad:
            # load() is now an async coroutine; legacy code "fired and forgot" it.
            # Schedule it in the running loop. onInit is invoked from getSharedObject
            # which is always reached from inside a coroutine (websocket handler).
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.load())
            except RuntimeError:
                # No loop yet: defer until manager calls _post_init (rare, init-time tools)
                logger.debug('autoLoad deferred: no running loop for %s', self.shared_id)

    def onSubscribePage(self, page_id):
        pass

    def onUnsubscribePage(self, page_id):
        pass

    def onDestroy(self):
        logger.debug('onDestroy %s', self.shared_id)
        if self.autoSave:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.save())
            except RuntimeError:
                pass

    def onShutdown(self):
        if self.autoSave:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.save())
            except RuntimeError:
                pass

    def subscribe(self, page_id=None, **kwargs):
        page = self.server.pages[page_id]
        privilege = self.checkPermission(page)
        if privilege:
            page.sharedObjects.add(self.shared_id)
            subkwargs = dict(kwargs)
            subkwargs['page_id'] = page_id
            subkwargs['user'] = page.user
            self.subscribed_pages[page_id] = subkwargs
            self.server.sharedStatus.sharedObjectSubscriptionAddPage(
                self.shared_id, page_id, subkwargs,
            )
            self.onSubscribePage(page)
            return dict(privilege=privilege, data=self.data)

    def unsubscribe(self, page_id=None):
        self.subscribed_pages.pop(page_id, None)
        self.server.sharedStatus.sharedObjectSubscriptionRemovePage(self.shared_id, page_id)
        self.onUnsubscribePage(page_id)
        if not self.subscribed_pages:
            self.timeout = self.server.delayedCall(
                self.expire, self.manager.removeSharedObject, self,
            )

    def checkPermission(self, page):
        privilege = 'readwrite'
        gnrapp = self.server.gnrapp
        if self.read_tags and not gnrapp.checkResourcePermission(self.read_tags, page.userTags):
            privilege = None
        elif self.write_tags and not gnrapp.checkResourcePermission(self.write_tags, page.userTags):
            privilege = 'readonly'
        return privilege

    @lockedCoroutine
    def datachange(self, page_id=None, path=None, value=None, attr=None,
                   evt=None, fired=None, **kwargs):
        if fired:
            data = Bag(dict(value=value, attr=attr, path=path,
                            shared_id=self.shared_id, evt=evt, fired=fired))
            return self.broadcast(
                command='som.sharedObjectChange', data=data, from_page_id=page_id,
            )
        path = 'root' if not path else 'root.%s' % path
        if evt == 'del':
            self._data.popNode(path, _reason=page_id)
        else:
            self._data.setItem(path, value, _attributes=attr, _reason=page_id)

    def _on_data_trigger(self, node=None, ind=None, evt=None, pathlist=None,
                         reason=None, **kwargs):
        self.changes = True
        if reason == 'autocreate':
            return
        plist = pathlist[1:]
        if evt == 'ins' or evt == 'del':
            plist = plist + [node.label]
        path = '.'.join(plist)
        data = Bag(dict(value=node.value, attr=node.attr, path=path,
                        shared_id=self.shared_id, evt=evt))
        from_page_id = reason
        # _on_data_trigger is a sync callback fired by gnrbag during setItem/popNode.
        # broadcast() is now async; schedule it on the running loop.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(
                command='som.sharedObjectChange', data=data, from_page_id=from_page_id,
            ))
        except RuntimeError:
            logger.debug('broadcast deferred: no running loop')

    def onPathFocus(self, page_id=None, curr_path=None, focused=None):
        if focused:
            self.focusedPaths[curr_path] = page_id
        else:
            self.focusedPaths.pop(curr_path, None)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(
                command='som.onPathLock', from_page_id=page_id,
                data=Bag(dict(locked=focused, lock_path=curr_path)),
            ))
        except RuntimeError:
            pass

    async def broadcast(self, command=None, data=None, from_page_id=None):
        envelope = Bag(dict(command=command, data=data)).toXml()
        channels = self.server.channels
        for p in list(self.subscribed_pages.keys()):
            if p != from_page_id:
                target = channels.get(p)
                if target is not None:
                    try:
                        await target.write_message(envelope)
                    except Exception:
                        logger.exception('broadcast failed for page %s', p)


class SqlSharedObject(SharedObject):
    pass


class SharedLogger(SharedObject):
    def onInit(self, **kwargs):
        logger.debug('onInit %s', self.shared_id)

    def onSubscribePage(self, page_id):
        logger.debug('onSubscribePage %s %s', self.shared_id, page_id)

    def onUnsubscribePage(self, page_id):
        logger.debug('onUnsubscribePage %s %s', self.shared_id, page_id)

    def onDestroy(self):
        logger.debug('onDestroy %s', self.shared_id)


class SharedStatus(SharedObject):
    def onInit(self, **kwargs):
        self.data['users'] = Bag()
        self.data['sharedObjects'] = Bag()

    @property
    def users(self):
        return self.data['users']

    @property
    def sharedObjects(self):
        return self.data['sharedObjects']

    def registerPage(self, page):
        page_item = page.page_item
        users = self.users
        page_id = page.page_id
        if page.user not in users:
            users[page.user] = Bag(dict(
                start_ts=page_item['start_ts'], user=page.user, connections=Bag(),
            ))
        userbag = users[page.user]
        connection_id = page.connection_id
        if connection_id not in userbag['connections']:
            userbag['connections'][connection_id] = Bag(dict(
                start_ts=page_item['start_ts'],
                user_ip=page_item['user_ip'],
                user_agent=page_item['user_agent'],
                connection_id=connection_id,
                pages=Bag(),
            ))
        userbag['connections'][connection_id]['pages'][page_id] = Bag(dict(
            pagename=page_item['pagename'],
            relative_url=page_item['relative_url'],
            start_ts=page_item['start_ts'],
            page_id=page_id,
        ))

    def unregisterPage(self, page):
        users = self.users
        userbag = users[page.user]
        connection_id = page.connection_id
        userconnections = userbag['connections']
        connection_pages = userconnections[connection_id]['pages']
        connection_pages.popNode(page.page_id)
        if not connection_pages:
            userconnections.popNode(connection_id)
            if not userconnections:
                users.popNode(page.user)

    def onPing(self, page_id, lastEventAge):
        page = self.server.pages.get(page_id)
        if not page:
            return
        userdata = self.users[page.user]
        conndata = userdata['connections'][page.connection_id]
        pagedata = conndata['pages'][page_id]
        pagedata['lastEventAge'] = lastEventAge
        conndata['lastEventAge'] = min(
            conndata['pages'].digest('#v.lastEventAge'), key=lambda i: i or 0,
        )
        userdata['lastEventAge'] = min(
            userdata['connections'].digest('#v.lastEventAge'), key=lambda i: i or 0,
        )

    def onUserEvent(self, page_id, event):
        page = self.server.pages.get(page_id)
        if not page:
            return
        pagedata = self.users[page.user]['connections'][page.connection_id]['pages'][page_id]
        old_targetId = pagedata['evt_targetId']
        for k, v in list(event.items()):
            pagedata['evt_%s' % k] = v
        if old_targetId == event['targetId']:
            if event['type'] == 'keypress':
                pagedata['typing'] = True
        else:
            pagedata['typing'] = False

    def registerSharedObject(self, shared_id, sharingkw):
        self.sharedObjects[shared_id] = Bag(sharingkw)

    def unregisterSharedObject(self, shared_id):
        self.sharedObjects.pop(shared_id)

    def sharedObjectSubscriptionAddPage(self, shared_id, page_id, subkwargs):
        self.sharedObjects[shared_id]['subscriptions'][page_id] = Bag(subkwargs)

    def sharedObjectSubscriptionRemovePage(self, shared_id, page_id):
        self.sharedObjects[shared_id]['subscriptions'].pop(page_id, None)


class SharedObjectsManager:
    def __init__(self, server, gc_interval=5):
        self.server = server
        self.sharedObjects = dict()
        # Legacy carried a tornado queues.Queue here for buffered changes
        # (consume_change_queue method, fully commented out). Drop it.

    def getSharedObject(self, shared_id, expire=None, startData=None,
                        read_tags=None, write_tags=None, factory=None, **kwargs):
        if factory is None:
            factory = SharedObject
        if shared_id not in self.sharedObjects:
            self.sharedObjects[shared_id] = factory(
                self, shared_id=shared_id, expire=expire, startData=startData,
                read_tags=read_tags, write_tags=write_tags, **kwargs,
            )
            sharingkw = dict(kwargs)
            sharingkw.update(dict(
                shared_id=shared_id, expire=expire,
                read_tags=read_tags, write_tags=write_tags,
                subscriptions=Bag(),
            ))
            # Avoid recursion: __global_status__ is itself a SharedObject and
            # registers itself on first access via sharedStatus property.
            if shared_id != '__global_status__':
                self.server.sharedStatus.registerSharedObject(shared_id, sharingkw)
        return self.sharedObjects[shared_id]

    def removeSharedObject(self, so):
        if so.onDestroy() is not False:
            self.sharedObjects.pop(so.shared_id, None)
            self.server.sharedStatus.unregisterSharedObject(so.shared_id)

    def do_unsubscribe(self, shared_id=None, page_id=None, **kwargs):
        sharedObject = self.sharedObjects.get(shared_id)
        if sharedObject:
            sharedObject.unsubscribe(page_id=page_id)

    def do_subscribe(self, shared_id=None, page_id=None, **kwargs):
        sharedObject = self.getSharedObject(shared_id, **kwargs)
        subscription = sharedObject.subscribe(page_id)
        if not subscription:
            subscription = dict(privilege='forbidden', data=Bag())
        elif sharedObject.timeout:
            sharedObject.timeout.cancel()
            sharedObject.timeout = None
        data = Bag(dict(
            value=subscription['data'], shared_id=shared_id,
            evt='init', privilege=subscription['privilege'],
        ))
        envelope = Bag(dict(command='som.sharedObjectChange', data=data))
        return envelope

    async def do_datachange(self, shared_id=None, **kwargs):
        if shared_id in self.sharedObjects:
            await self.sharedObjects[shared_id].datachange(**kwargs)

    async def do_saveSharedObject(self, shared_id=None, **kwargs):
        await self.sharedObjects[shared_id].save()

    async def do_loadSharedObject(self, shared_id=None, **kwargs):
        await self.getSharedObject(shared_id).load()

    def do_dispatch(self, shared_id=None, so_method=None, so_pars=None, **kwargs):
        so = self.getSharedObject(shared_id)
        pars = so_pars or dict()
        return getattr(so, so_method)(**pars)

    def onShutdown(self):
        for so in list(self.sharedObjects.values()):
            so.onShutdown()

    def do_onPathFocus(self, shared_id=None, page_id=None, curr_path=None,
                       focused=None, **kwargs):
        self.sharedObjects[shared_id].onPathFocus(
            page_id=page_id, curr_path=curr_path, focused=focused,
        )


class AsyncWebSocketHandler(_LegacyAsyncWebSocketHandler):
    """Override of the legacy AsyncWebSocketHandler.

    The legacy class assumed Tornado's write_message was a sync method that
    schedules the send on the IOLoop. With aiohttp, GnrWebSocketSession
    .write_message is a coroutine. Callers come from two contexts:

    - inside the event loop (e.g. SharedObject.broadcast, DebugSession):
      they should ``await`` write_message directly. They use this handler
      via ``server.wsk.sendCommandToPage`` which we now route through the
      session's coroutine method via run_coroutine_threadsafe.
    - from a threadpool worker (e.g. page methods called from do_call):
      run_coroutine_threadsafe schedules the send on the loop and returns
      a concurrent.futures.Future the worker can ignore.
    """

    def __init__(self, server):
        self.server = server

    def _send(self, target, envelope_xml):
        loop = self.server.loop
        coro = target.write_message(envelope_xml)
        if loop is None or not loop.is_running():
            logger.warning('AsyncWebSocketHandler.sendCommandToPage called with no running loop')
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            # Already inside the loop: schedule as task, don't block.
            loop.create_task(coro)
        else:
            # From a thread (e.g. threadpool worker): schedule on the loop.
            asyncio.run_coroutine_threadsafe(coro, loop)

    def sendCommandToPage(self, page_id, command, data):
        envelope = Bag(dict(command=command, data=data))
        target = self.server.channels.get(page_id)
        if target is None:
            return
        self._send(target, envelope.toXml(unresolved=True))


class GnrWebSocketSession:
    """Per-connection state for an aiohttp WebSocket.

    Replaces the legacy GnrWebSocketHandler (Tornado WebSocketHandler subclass).
    The handler function ``websocket_handler`` instantiates one of these per
    incoming connection and dispatches messages here.

    Methods are kept compatible with the legacy ``do_*`` convention so that
    SharedObjectsManager and any external proxy keep their dispatch contract.
    """

    def __init__(self, server, ws):
        self.server = server
        self.ws = ws
        self._page_id = None

    # ---- properties mirroring legacy GnrBaseHandler --------------------
    @property
    def channels(self):
        return self.server.channels

    @property
    def remote_services(self):
        return self.server.remote_services

    @property
    def pages(self):
        return self.server.pages

    @property
    def page(self):
        return self.pages[self.page_id]

    @property
    def page_id(self):
        return self._page_id

    @page_id.setter
    def page_id(self, value):
        self._page_id = value

    @property
    def gnrsite(self):
        return self.server.gnrsite

    @property
    def debug_queues(self):
        return self.server.debug_queues

    # ---- writer used by SharedObject.broadcast and DebugSession --------
    async def write_message(self, msg):
        """Async writer used by code paths that already run in the loop.

        Mirrors the legacy ``write_message`` name. Coroutine-only: callers
        from other coroutines must ``await`` it. There are no remaining
        sync callers after the migration.
        """
        if not self.ws.closed:
            await self.ws.send_str(msg)

    # ---- dispatch ------------------------------------------------------
    def parseMessage(self, message):
        kwargs = fromJson(message)
        catalog = self.server.gnrapp.catalog
        result = dict()
        for k, v in list(kwargs.items()):
            k = k.strip()
            if isinstance(v, (bytes, str)):
                try:
                    v = catalog.fromTypedText(v)
                    result[k] = v
                except Exception:
                    raise
            else:
                result[k] = v
        command = result.pop('command')
        result_token = result.pop('result_token', None)
        return command, result_token, result

    def getHandler(self, command, kwargs):
        if '.' not in command:
            return getattr(self, 'do_%s' % command, self.wrongCommand)
        kwargs['page_id'] = self.page_id
        proxy = self.server
        while '.' in command:
            proxyname, command = command.split('.', 1)
            proxy = getattr(proxy, proxyname, None)
        if proxy is None:
            return self.wrongCommand
        return getattr(proxy, 'do_%s' % command, self.wrongCommand)

    def getExecutor(self, method):
        executor = getattr(method, '_executor', None)
        if executor:
            return self.server.executors.get(executor)

    async def on_message(self, message):
        command, result_token, kwargs = self.parseMessage(message)
        handler = self.getHandler(command, kwargs)
        if handler is None:
            return
        if getattr(handler, '_executor', None) == 'threadpool':
            loop = asyncio.get_running_loop()
            executor = self.server.executors['threadpool']
            result = await loop.run_in_executor(
                executor,
                functools.partial(handler, _time_start=time.time(), **kwargs),
            )
        else:
            result = handler(_time_start=time.time(), **kwargs)
            if inspect.isawaitable(result):
                result = await result
        if result_token:
            result = Bag(dict(token=result_token, envelope=result)).toXml(unresolved=True)
        if result is not None:
            await self.write_message(result)

    def on_close(self):
        self.channels.pop(self.page_id, None)
        self.server.unregisterPage(page_id=self.page_id)

    # ---- do_* command handlers (parity with legacy) --------------------
    def wrongCommand(self, command=None, **kwargs):
        return 'WRONG COMMAND: %s' % command

    def do_echo(self, data=None, **kwargs):
        return data

    async def do_ping(self, lastEventAge=None, **kwargs):
        if self._page_id is not None:
            self.server.sharedStatus.onPing(self._page_id, lastEventAge)
        await self.write_message('pong')

    def do_user_event(self, event=None, **kwargs):
        self.server.sharedStatus.onUserEvent(self._page_id, event)

    async def do_route(self, target_page_id=None, envelope=None, **kwargs):
        target = self.channels.get(target_page_id)
        if target is not None:
            await target.write_message(envelope)

    def do_register_service(self, page_id=None, gateway_service=None, **kwargs):
        if gateway_service:
            self.remote_services[gateway_service] = page_id
        self.do_connected(page_id=page_id, **kwargs)

    @threadpool
    def do_service(self, gateway_service=None, **kwargs):
        service = self.gnrsite.getService(
            service_type='remotewsservice', service_name=gateway_service,
        )
        if service and hasattr(service, 'on_message'):
            service.on_message(**kwargs)

    def do_connected(self, page_id=None, **kwargs):
        self._page_id = page_id
        if page_id not in self.channels:
            self.channels[page_id] = self
        if page_id not in self.pages:
            self.server.registerPage(page_id=page_id)

    def do_pdb_command(self, cmd=None, pdb_id=None, **kwargs):
        debugkey = '%s,%s' % (self.page_id, pdb_id)
        queue = self.debug_queues.get(debugkey)
        if queue is None:
            queue = asyncio.Queue(maxsize=40)
            self.debug_queues[debugkey] = queue
        queue.put_nowait(cmd)

    @threadpool
    def do_call(self, method=None, _time_start=None, **kwargs):
        error = None
        result = None
        resultAttrs = None
        # Legacy code resets page._db once before calling getWsMethod twice;
        # the double getWsMethod is not load-bearing — keep one call.
        self.page._db = None
        handler = self.page.getWsMethod(method)
        if handler:
            try:
                result = handler(**kwargs)
                if isinstance(result, tuple):
                    result, resultAttrs = result
            except Exception as e:
                result = TraceBackResolver()()
                error = str(e)
        envelope = Bag()
        envelope.setItem(
            'data', result,
            _attributes=resultAttrs, _server_time=time.time() - _time_start,
        )
        if error:
            envelope.setItem('error', error)
        return envelope


async def websocket_handler(request):
    """aiohttp request handler for /websocket.

    Replaces tornado.websocket.WebSocketHandler subclass dispatch with the
    async-iteration pattern recommended by aiohttp.
    """
    server = request.app['server']
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    session = GnrWebSocketSession(server, ws)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    await session.on_message(msg.data)
                except Exception:
                    logger.exception('error handling websocket message')
            elif msg.type == WSMsgType.ERROR:
                logger.warning('websocket connection closed with exception %s',
                               ws.exception())
                break
    finally:
        session.on_close()
    return ws


async def wsproxy_handler(request):
    """aiohttp POST handler for /wsproxy.

    Replaces the legacy GnrWsProxyHandler (Tornado RequestHandler).
    Used by WSGI workers (gunicorn) and any external publisher that needs
    to push a message to one or more browser pages over the WebSocket.

    Form fields (urlencoded body):
    - page_id: target page id, comma-separated list, '*' to broadcast,
      or empty if remote_service is given.
    - envelope: XML payload of a Bag(command=..., data=...).
    - remote_service: optional gateway service name; the server resolves
      it to a registered page_id via self.remote_services.

    With no page_id and no remote_service the envelope is decoded and
    dispatched as a server-side externalCommand.
    """
    server = request.app['server']
    form = await request.post()
    page_id = form.get('page_id') or ''
    envelope = form.get('envelope') or ''
    remote_service = form.get('remote_service') or ''

    if remote_service:
        page_id = server.remote_services.get(remote_service) or ''
        if not page_id:
            return web.Response(text='')

    if not page_id:
        bag = Bag(envelope)
        command = bag['command']
        data = bag['data']
        server.externalCommand(command, data)
        return web.Response(text='')

    if page_id == '*':
        page_ids = list(server.channels.keys())
    else:
        page_ids = page_id.split(',')

    for dest_page_id in page_ids:
        target = server.channels.get(dest_page_id)
        if target is not None:
            try:
                await target.write_message(envelope)
            except Exception:
                logger.exception('wsproxy send failed for page %s', dest_page_id)
    return web.Response(text='')


class GnrBaseAsyncServer:
    """Async server based on aiohttp + asyncio.

    Mirrors the public surface of the legacy GnrBaseAsyncServer
    (gnrasync.py): same constructor signature, same attributes
    (channels, pages, remote_services, executors, gnrsite, gnrapp, db,
    site_options) and the same start() entry point.
    """

    def __init__(self, port=None, instance=None, ssl_crt=None, ssl_key=None,
                 autoreload=None, site_options=None):
        self.port = port
        self.handlers = []
        self.executors = dict()
        self.channels = dict()
        self.remote_services = dict()
        self.pages = dict()
        self.debug_queues = dict()
        self.gnrsite = GnrWsgiSite(instance)
        self.instance_name = self.gnrsite.site_name
        self.gnrsite.ws_site = self
        self.gnrapp = self.gnrsite.gnrapp
        self.db = self.gnrapp.db
        self.ssl_key = ssl_key
        self.ssl_crt = ssl_crt
        self.site_options = site_options or dict()
        self.autoreload = autoreload  # accepted for CLI compat
        self.som = SharedObjectsManager(self)
        self.wsk = AsyncWebSocketHandler(self)
        self.app = None
        self.runner = None
        self.loop = None  # set by _run() when the event loop starts
        self._shutdown_event = None

    # ---- API used by external callers (kept identical to legacy) ----
    def delayedCall(self, delay, cb, *args, **kwargs):
        return DelayedCall(self, delay, cb, *args, **kwargs)

    def addHandler(self, path, handler, options=None):
        if options:
            self.handlers.append((path, handler, options))
        else:
            self.handlers.append((path, handler))

    def addExecutor(self, name, executor):
        self.executors[name] = executor

    def externalCommand(self, command, data):
        handler = getattr(self, 'do_%s' % command)
        handler(**data.asDict(ascii=True))

    def do_registerNewPage(self, page_id=None, page_info=None, class_info=None,
                           init_info=None, mixin_set=None):
        if not class_info:
            return
        page = self.gnrsite.resource_loader.instantiate_page(
            page_id=page_id, class_info=class_info,
            init_info=init_info, page_info=page_info,
        )
        self.registerPage(page)

    def registerPage(self, page=None, page_id=None):
        if not page:
            page = self.gnrsite.resource_loader.get_page_by_id(page_id)
            if not page:
                logger.warning('page %s not existing in gnrdaemon register', page_id)
                return
            logger.info('page %s restored successfully from gnrdaemon register', page_id)
        page.asyncServer = self
        page.sharedObjects = set()
        self.pages[page.page_id] = page
        self.sharedStatus.registerPage(page)

    def unregisterPage(self, page_id):
        page = self.pages.get(page_id)
        if not page:
            return
        if page.sharedObjects:
            for shared_id in page.sharedObjects:
                so = self.som.sharedObjects.get(shared_id)
                if so is not None:
                    so.unsubscribe(page_id)
        self.sharedStatus.unregisterPage(page)
        self.pages.pop(page_id, None)

    @property
    def sharedStatus(self):
        return self.som.getSharedObject(
            '__global_status__', expire=-1,
            read_tags='_DEV_,superadmin', write_tags='__SYSTEM__',
            factory=SharedStatus,
        )

    @property
    def errorStatus(self):
        return self.som.getSharedObject(
            '__error_status__', expire=-1, startData=dict(users=Bag()),
            read_tags='_DEV_,superadmin', write_tags='__SYSTEM__',
            factory=SharedLogger,
        )

    def logToPage(self, page_id, **kwargs):
        self.pages[page_id].log(**kwargs)

    # ---- aiohttp wiring -----------------------------------------------
    def _build_app(self):
        app = web.Application()
        app['server'] = self
        app.router.add_get('/websocket', websocket_handler)
        app.router.add_post('/wsproxy', wsproxy_handler)
        return app

    def _build_ssl_context(self):
        if not (self.ssl_crt and self.ssl_key):
            return None
        ctx = ssl_module.create_default_context(ssl_module.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(self.ssl_crt, self.ssl_key)
        return ctx

    def _ensure_sockets_dir(self):
        sockets_dir = os.path.join(self.gnrsite.site_path, 'sockets')
        if len(sockets_dir) > 90:
            sockets_dir = os.path.join(
                '/tmp',
                os.path.basename(self.gnrsite.instance_path),
                'gnr_sock',
            )
        if not os.path.exists(sockets_dir):
            os.makedirs(sockets_dir)
        return sockets_dir

    async def _run(self):
        self.loop = asyncio.get_running_loop()
        self.app = self._build_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        sockets_dir = self._ensure_sockets_dir()
        socket_path = os.path.join(sockets_dir, 'async.sock')
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        unix_site = web.UnixSite(self.runner, socket_path)
        await unix_site.start()
        os.chmod(socket_path, 0o666)
        logger.info('aiohttp server bound to unix socket %s', socket_path)

        if self.port:
            tcp_site = web.TCPSite(
                self.runner,
                host='0.0.0.0',
                port=int(self.port),
                ssl_context=self._build_ssl_context(),
            )
            await tcp_site.start()
            logger.info('aiohttp server listening on TCP port %s', self.port)

        # Phase 6 wires the debugger TCP server here.

        self._shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._on_signal)
        await self._shutdown_event.wait()
        await self._cleanup()

    def _on_signal(self):
        if self._shutdown_event and not self._shutdown_event.is_set():
            self._shutdown_event.set()

    async def _cleanup(self):
        try:
            await asyncio.wait_for(
                self.runner.cleanup(),
                timeout=MAX_WAIT_SECONDS_BEFORE_SHUTDOWN,
            )
        except asyncio.TimeoutError:
            logger.warning('shutdown timeout exceeded')

    def start(self):
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            pass


class GnrAsyncServer(GnrBaseAsyncServer):
    """Concrete server with the threadpool executor and websocket route."""

    def __init__(self, *args, **kwargs):
        # Drop the legacy `web=True` kwarg (Phase 7); kept silent for compat
        # so existing callers (serverwsgi.py and CLI) need no churn yet.
        kwargs.pop('web', None)
        super().__init__(*args, **kwargs)
        self.addExecutor('threadpool', ThreadPoolExecutor(max_workers=20))


if __name__ == '__main__':
    server = GnrAsyncServer(port=8888, instance='sandbox')
    server.start()
