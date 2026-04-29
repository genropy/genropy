# -*- coding: utf-8 -*-
"""End-to-end tests for the asyncio/aiohttp gnrasync server.

GnrWsgiSite is mocked at the boundary because instantiating it requires a
fully provisioned GenroPy instance with a database schema; the websocket
server itself runs real aiohttp and asyncio code (no mocked transport)."""

import asyncio
import json
import os
import sys
import urllib.parse

import pytest

if sys.platform == 'win32':
    pytest.skip(
        'gnrasync requires AF_UNIX sockets which are not fully supported on Windows',
        allow_module_level=True,
    )

import aiohttp
from unittest.mock import MagicMock, patch

from gnr.core.gnrbag import Bag
from gnr.web.gnrasync import GnrAsyncServer


PORT_BASE = 9850


def _build_server(tmp_path, port):
    """Spawn a GnrAsyncServer with GnrWsgiSite mocked.

    The site filesystem path lives under pytest tmp_path so each test gets
    its own sockets directory and the real aiohttp UnixSite/TCPSite bind
    cleanly without colliding between tests.
    """
    site = MagicMock()
    site.site_name = 'gnrasync_test'
    site.site_path = str(tmp_path)
    site.instance_path = str(tmp_path / 'instance')
    catalog = MagicMock()
    catalog.fromTypedText = lambda v: v
    site.gnrapp.catalog = catalog
    site.gnrapp.db = MagicMock()
    site.gnrapp.checkResourcePermission = lambda tags, user_tags: True

    with patch('gnr.web.gnrasync.GnrWsgiSite', return_value=site):
        server = GnrAsyncServer(port=port, instance='dummy')

    fake_page = MagicMock()
    fake_page.page_id = 'pg1'
    fake_page.user = 'u'
    fake_page.userTags = 'admin'
    fake_page.connection_id = 'c1'
    fake_page.page_item = {
        'start_ts': 'ts', 'user_ip': '127.0.0.1', 'user_agent': 'pytest',
        'pagename': 'p', 'relative_url': '/',
    }
    fake_page.sharedObjects = set()
    server.pages['pg1'] = fake_page
    return server, fake_page


@pytest.mark.asyncio
async def test_ping_pong(tmp_path):
    server, fake_page = _build_server(tmp_path, PORT_BASE)
    run_task = asyncio.create_task(server._run())
    try:
        await asyncio.sleep(0.4)
        server.sharedStatus.registerPage(fake_page)
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(f'ws://127.0.0.1:{PORT_BASE}/websocket') as ws:
                await ws.send_str(json.dumps({'command': 'connected', 'page_id': 'pg1'}))
                await asyncio.sleep(0.1)
                await ws.send_str(json.dumps({'command': 'ping', 'lastEventAge': 0}))
                msg = await asyncio.wait_for(ws.receive(), timeout=2)
                assert msg.data == 'pong'
    finally:
        server._on_signal()
        await run_task


@pytest.mark.asyncio
async def test_echo_with_result_token(tmp_path):
    server, fake_page = _build_server(tmp_path, PORT_BASE + 1)
    run_task = asyncio.create_task(server._run())
    try:
        await asyncio.sleep(0.4)
        server.sharedStatus.registerPage(fake_page)
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(f'ws://127.0.0.1:{PORT_BASE + 1}/websocket') as ws:
                await ws.send_str(json.dumps({'command': 'connected', 'page_id': 'pg1'}))
                await asyncio.sleep(0.1)
                await ws.send_str(json.dumps({
                    'command': 'echo', 'result_token': 'tok1', 'data': 'hello',
                }))
                msg = await asyncio.wait_for(ws.receive(), timeout=2)
                assert '<token>tok1</token>' in msg.data
                assert 'hello' in msg.data
    finally:
        server._on_signal()
        await run_task


@pytest.mark.asyncio
async def test_wsproxy_push(tmp_path):
    server, fake_page = _build_server(tmp_path, PORT_BASE + 2)
    run_task = asyncio.create_task(server._run())
    try:
        await asyncio.sleep(0.4)
        server.sharedStatus.registerPage(fake_page)
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(f'ws://127.0.0.1:{PORT_BASE + 2}/websocket') as ws:
                await ws.send_str(json.dumps({'command': 'connected', 'page_id': 'pg1'}))
                await asyncio.sleep(0.1)

                # POST /wsproxy over the unix socket — the same path used by
                # gunicorn workers via WsgiWebSocketHandler.
                envelope = Bag(dict(command='alert', data='from-wsproxy')).toXml(unresolved=True)
                body = urllib.parse.urlencode(dict(
                    page_id='pg1', remote_service='', envelope=envelope,
                ))
                sock = os.path.join(server._ensure_sockets_dir(), 'async.sock')
                connector = aiohttp.UnixConnector(path=sock)
                async with aiohttp.ClientSession(connector=connector) as cs:
                    async with cs.post(
                        'http://localhost/wsproxy',
                        data=body,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    ) as resp:
                        assert resp.status == 200

                msg = await asyncio.wait_for(ws.receive(), timeout=2)
                assert 'from-wsproxy' in msg.data
                assert '<command>alert</command>' in msg.data
    finally:
        server._on_signal()
        await run_task


@pytest.mark.asyncio
async def test_shared_object_subscribe_and_datachange(tmp_path):
    server, fake_page = _build_server(tmp_path, PORT_BASE + 3)
    run_task = asyncio.create_task(server._run())
    try:
        await asyncio.sleep(0.4)
        server.sharedStatus.registerPage(fake_page)
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(f'ws://127.0.0.1:{PORT_BASE + 3}/websocket') as ws:
                await ws.send_str(json.dumps({'command': 'connected', 'page_id': 'pg1'}))
                await asyncio.sleep(0.1)

                await ws.send_str(json.dumps({
                    'command': 'som.subscribe', 'result_token': 's1',
                    'shared_id': 'state', 'page_id': 'pg1',
                }))
                msg = await asyncio.wait_for(ws.receive(), timeout=2)
                assert '<token>s1</token>' in msg.data
                assert 'init' in msg.data

                await ws.send_str(json.dumps({
                    'command': 'som.datachange',
                    'shared_id': 'state', 'page_id': 'pg1',
                    'path': 'foo.bar', 'value': 'hi', 'evt': 'set',
                }))
                await asyncio.sleep(0.2)
                so = server.som.sharedObjects['state']
                assert so.data['foo.bar'] == 'hi'
    finally:
        server._on_signal()
        await run_task


@pytest.mark.asyncio
async def test_unix_sockets_created(tmp_path):
    server, _ = _build_server(tmp_path, PORT_BASE + 4)
    run_task = asyncio.create_task(server._run())
    try:
        await asyncio.sleep(0.4)
        # site_path may exceed 90 chars on macOS, in which case the server
        # falls back to /tmp/<instance>/gnr_sock — resolve via the same helper.
        sockets_dir = server._ensure_sockets_dir()
        assert os.path.exists(os.path.join(sockets_dir, 'async.sock'))
        assert os.path.exists(os.path.join(sockets_dir, 'debugger.sock'))
    finally:
        server._on_signal()
        await run_task


@pytest.mark.asyncio
async def test_no_tornado_import():
    """The migration deletes the tornado dependency entirely."""
    import gnr.web.gnrasync as mod
    src = open(mod.__file__).read()
    assert 'import tornado' not in src
    assert 'from tornado' not in src

    async_dir = os.path.dirname(mod.__file__)
    assert not os.path.exists(os.path.join(async_dir, 'tornado_wsgi.py'))
