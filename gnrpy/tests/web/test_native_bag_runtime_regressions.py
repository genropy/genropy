"""Runtime regressions found while exercising the native Bag integration."""

import asyncio
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from gnr.web.gnrasync import GnrAsyncServer
from gnr.web.serverwsgi import Server


def _unix_only_async_server(tmp_path):
    site = MagicMock()
    site.site_name = "native_bag_runtime_" + uuid.uuid4().hex[:12]
    site.site_path = str(tmp_path)
    site.instance_path = str(tmp_path / tmp_path.name)
    site.gnrapp.catalog.fromTypedText.side_effect = lambda value: value
    site.gnrapp.checkResourcePermission.side_effect = lambda *_args: True

    with patch("gnr.web.gnrasync.GnrWsgiSite", return_value=site):
        return GnrAsyncServer(port=None, instance="dummy")


@pytest.mark.skipif(sys.platform == "win32", reason="AF_UNIX is unavailable")
@pytest.mark.asyncio
async def test_async_server_accepts_a_real_request_on_its_unix_listener(tmp_path):
    """Accepting AF_UNIX traffic must not attempt TCP keepalive setup."""
    server = _unix_only_async_server(tmp_path)
    run_task = asyncio.create_task(server._run())
    socket_dir = server._ensure_sockets_dir()
    socket_path = os.path.join(socket_dir, "async.sock")
    try:
        for _attempt in range(100):
            if os.path.exists(socket_path):
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail("async Unix listener was not created")

        connector = aiohttp.UnixConnector(path=socket_path)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "http://localhost/wsproxy",
                data={"page_id": "missing", "envelope": "unused"},
            ) as response:
                assert response.status == 200
                assert await response.text() == ""
    finally:
        server._on_signal()
        await asyncio.wait_for(run_task, timeout=5)
        if socket_dir.startswith("/tmp/"):
            shutil.rmtree(Path(socket_dir).parent, ignore_errors=True)


@pytest.mark.skipif(sys.platform == "win32", reason="AF_UNIX is unavailable")
def test_wsgi_probe_uses_the_async_servers_long_path_fallback(tmp_path):
    """The WSGI probe and async server must agree when site paths are long."""
    fallback_root = Path(tempfile.mkdtemp(prefix="gnr_socket_probe_", dir="/tmp"))
    server = object.__new__(Server)
    server.site_name = fallback_root.name
    server.site_path = str(tmp_path / ("long-site-segment-" * 8))
    socket_dir = fallback_root / "gnr_sock"
    socket_dir.mkdir()
    socket_path = socket_dir / "async.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(socket_path))
        listener.listen(1)
        assert server._async_server_already_running() is True

        listener.close()
        assert server._async_server_already_running() is False
    finally:
        listener.close()
        shutil.rmtree(fallback_root)


def test_native_site_dojo_version_is_explicit_text(tmp_path):
    from genro_bag import Bag as NativeBag

    # Instance configuration must retain the version as text for URL joining.
    # Keep this fixture independent of private development instances.
    site_config = tmp_path / "siteconfig.xml"
    site_config.write_text('<GenRoBag><dojo version="11::T"/></GenRoBag>')
    config = NativeBag(str(site_config))
    version = config["dojo?version"]
    assert version == "11"
    assert '/'.join((version, 'dojo', 'dojo.js')) == '11/dojo/dojo.js'
