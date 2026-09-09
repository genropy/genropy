"""Explicit provider selection must leave classic installations untouched."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE = Path(__file__).resolve().parents[2]


def run_import(provider, code, provider_source=None):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        metadata = root / 'wsk_test_provider-1.0.dist-info'
        metadata.mkdir()
        (metadata / 'METADATA').write_text(
            'Metadata-Version: 2.1\nName: wsk-test-provider\nVersion: 1.0\n')
        (metadata / 'entry_points.txt').write_text(
            '[gnr.web]\nwebsockethandler = wsk_test_provider:Handler\n')
        (root / 'wsk_test_provider.py').write_text(provider_source or '''
class Handler:
    client_module = 'gnrwebsocket_asgi'
    def checkSocket(self):
        return True
    def sendCommandToPage(self, *args):
        pass
''')
        env = os.environ.copy()
        env.pop('GNR_DAEMON_PROVIDER', None)
        if provider:
            env['GNR_DAEMON_PROVIDER'] = provider
        env['PYTHONPATH'] = os.pathsep.join([directory, str(SOURCE)])
        return subprocess.run([sys.executable, '-c', code], env=env,
                              capture_output=True, text=True, timeout=20)


def test_installed_provider_is_not_discovered_without_explicit_selection():
    result = run_import(None, '''
import importlib.metadata
from unittest.mock import patch
with patch.object(importlib.metadata, 'entry_points', side_effect=AssertionError('discovery')):
    from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import WsgiWebSocketHandler, WebSocketHandler
assert WsgiWebSocketHandler.__module__ == 'gnr.web.gnrwsgisite_proxy.gnrwebsockethandler'
assert issubclass(WsgiWebSocketHandler, WebSocketHandler)
assert not hasattr(WsgiWebSocketHandler, 'client_module')
''')
    assert result.returncode == 0, result.stderr


def test_explicit_provider_selects_its_handler():
    result = run_import('wsk-test-provider', '''
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import WsgiWebSocketHandler
from wsk_test_provider import Handler
assert WsgiWebSocketHandler is Handler
''')
    assert result.returncode == 0, result.stderr


def test_unknown_provider_fails_explicitly():
    result = run_import('missing-provider', '''
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import WsgiWebSocketHandler
''')
    assert result.returncode != 0
    assert 'matches 0' in result.stderr


def test_invalid_provider_fails_explicitly():
    result = run_import('wsk-test-provider', '''
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import WsgiWebSocketHandler
''', provider_source='Handler = object\n')
    assert result.returncode != 0
    assert 'must export a handler class' in result.stderr
