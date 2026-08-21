"""Tests for the Pyro proxies the site register client talks to the daemon with.

No daemon is involved: the proxies are never connected, `Proxy._pyroInvoke` is
replaced with a stub so the retry behaviour can be observed on its own.
"""

import os
from multiprocessing import get_context
from threading import Lock

import Pyro4
import pytest

from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import MAX_RETRY_ATTEMPTS, OLD_HMAC_MODE
from gnr.web.daemon import siteregister_client as client_module
from gnr.web.daemon.siteregister_client import (
    RefreshingProxy,
    SiteRegisterClient,
    build_proxy,
)

TEST_URI = 'PYRO:SiteRegister@localhost:40000'
NEW_TEST_URI = 'PYRO:SiteRegister@localhost:40001'
REMOTE_URI = 'PYRO:RemoteData@localhost:40000'
NEW_REMOTE_URI = 'PYRO:RemoteData@localhost:40001'


class FlakyInvoke:
    """Stand-in for Proxy._pyroInvoke, failing its first `failures` calls."""

    def __init__(self, failures, result='ok'):
        self.failures = failures
        self.result = result
        self.calls = 0

    def __call__(self, methodname, vargs, kwargs, flags=0, objectId=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise Pyro4.errors.ConnectionClosedError(
                'sending: connection lost: [Errno 104] Connection reset by peer')
        return self.result


class FakeRegister:
    """Stand-in for the remote site register object."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def lock_item(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.result


class FakeProxy:
    def __init__(self, uri, responses, calls, released):
        self.uri = uri
        self.responses = responses
        self.calls = calls
        self.released = released

    def _pyroRelease(self):
        self.released.append(self.uri)

    def __getattr__(self, name):
        def remote(*args, **kwargs):
            self.calls.append((self.uri, name))
            result = self.responses[self.uri]
            if isinstance(result, Exception):
                raise result
            return result
        return remote


class LiveRegister:
    def __init__(self, value):
        self.value = value

    def get_item(self, *args, **kwargs):
        return self.value


def run_live_register(connection, value):
    Pyro4.config.SERIALIZER = 'pickle'
    Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
    daemon = Pyro4.Daemon(host='localhost', port=0)
    uri = daemon.register(LiveRegister(value), objectId='SiteRegister')
    connection.send(str(uri))
    connection.close()
    daemon.requestLoop()


def start_live_register(value):
    context = get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=run_live_register, args=(sender, value))
    process.start()
    uri = receiver.recv()
    receiver.close()
    return process, uri


def stop_live_register(process):
    process.terminate()
    process.join(timeout=2)


@pytest.fixture
def proxy(monkeypatch):
    monkeypatch.setattr(Pyro4.config, 'METADATA', False)
    return build_proxy(TEST_URI, hmac_key=b'secret')


def make_client(siteregister):
    client = SiteRegisterClient.__new__(SiteRegisterClient)
    client.siteregister = siteregister
    return client


def test_build_proxy_enables_retry(proxy):
    assert proxy._pyroMaxRetries == MAX_RETRY_ATTEMPTS
    if not OLD_HMAC_MODE:
        assert proxy._pyroHmacKey == b'secret'


def test_call_is_retried_after_a_dropped_connection(proxy):
    invoke = FlakyInvoke(failures=1)
    proxy._pyroInvoke = invoke
    assert proxy.get_item('page_id') == 'ok'
    assert invoke.calls == 2


def test_call_raises_when_every_attempt_fails(proxy):
    invoke = FlakyInvoke(failures=MAX_RETRY_ATTEMPTS + 1)
    proxy._pyroInvoke = invoke
    with pytest.raises(Pyro4.errors.ConnectionClosedError):
        proxy.get_item('page_id')
    assert invoke.calls == MAX_RETRY_ATTEMPTS + 1


def test_client_delegates_undeclared_methods_to_the_register():
    client = make_client(FakeRegister(result=True))
    assert client.lock_item('page_id') is True


def test_client_lets_remote_errors_propagate():
    client = make_client(FakeRegister(error=ValueError('boom')))
    with pytest.raises(ValueError):
        client.lock_item('page_id')


def fake_proxy_factory(monkeypatch, responses):
    calls = []
    released = []

    def factory(uri, hmac_key=None):
        return FakeProxy(uri, responses, calls, released)

    monkeypatch.setattr(client_module, 'build_proxy', factory)
    return calls, released


def test_refreshing_proxy_rebuilds_when_uri_changes(monkeypatch):
    error = Pyro4.errors.CommunicationError('old port refused')
    calls, released = fake_proxy_factory(
        monkeypatch, {TEST_URI: error, NEW_TEST_URI: 'ok'})
    proxy = RefreshingProxy(TEST_URI, refresh_uri=lambda failed: NEW_TEST_URI)

    assert proxy.get_item('page_id') == 'ok'
    assert calls == [(TEST_URI, 'get_item'), (NEW_TEST_URI, 'get_item')]
    assert released == [TEST_URI]


def test_refreshing_proxy_propagates_when_uri_is_unchanged(monkeypatch):
    error = Pyro4.errors.CommunicationError('daemon unavailable')
    calls, released = fake_proxy_factory(monkeypatch, {TEST_URI: error})
    proxy = RefreshingProxy(TEST_URI, refresh_uri=lambda failed: failed)

    with pytest.raises(Pyro4.errors.CommunicationError):
        proxy.get_item('page_id')
    assert calls == [(TEST_URI, 'get_item')]
    assert released == []


def test_live_proxy_recovers_on_a_new_port():
    old_process, old_uri = start_live_register('old')
    new_process = None
    current_uri = [old_uri]
    try:
        proxy = RefreshingProxy(old_uri, refresh_uri=lambda failed: current_uri[0])
        assert proxy.get_item('page_id') == 'old'
        new_process, current_uri[0] = start_live_register('new')
        stop_live_register(old_process)

        assert proxy.get_item('page_id') == 'new'
        assert proxy.uri == current_uri[0]
    finally:
        if old_process.is_alive():
            stop_live_register(old_process)
        if new_process:
            stop_live_register(new_process)


def test_existing_remote_store_re_resolves_after_port_change(monkeypatch):
    error = Pyro4.errors.CommunicationError('old port refused')
    calls, released = fake_proxy_factory(
        monkeypatch, {REMOTE_URI: error, NEW_REMOTE_URI: 'value'})
    client = SiteRegisterClient.__new__(SiteRegisterClient)
    client.hmac_key = b'secret'
    client.siteregister_uri = TEST_URI
    client.siteregisterserver_uri = 'PYRO:SiteRegisterServer@localhost:40000'
    client.remotebag_uri = REMOTE_URI
    client._uri_refresh_lock = Lock()
    client.resolveSiteRegisterUris = lambda: (
        'PYRO:SiteRegisterServer@localhost:40001', NEW_TEST_URI)
    record = {'register_name': 'global', 'register_item_id': '*'}
    client.add_data_to_register_item(record)

    assert record['data'].getItem('key') == 'value'
    assert client.siteregister_uri == NEW_TEST_URI
    assert client.remotebag_uri == NEW_REMOTE_URI
    assert record['data'].proxy.uri == NEW_REMOTE_URI
    assert calls == [(REMOTE_URI, 'getItem'), (NEW_REMOTE_URI, 'getItem')]
    assert released == [REMOTE_URI, REMOTE_URI]


def test_sitedaemon_uri_is_reloaded_from_xml(tmp_path):
    xml_path = tmp_path / 'sitedaemon.xml'
    data = Bag()
    data.setItem('params', None, pid=os.getpid(), main_uri='main',
                 register_uri=NEW_TEST_URI)
    data.toXml(str(xml_path))
    client = SiteRegisterClient.__new__(SiteRegisterClient)
    client.sitedaemon_xml_path = str(xml_path)

    assert client.readSitedaemonUris() == ('main', NEW_TEST_URI)


def test_central_daemon_resolves_current_site_uri():
    class FakeDaemon:
        def getSite(self, *args, **kwargs):
            return {'server_uri': 'main', 'register_uri': NEW_TEST_URI}

    client = SiteRegisterClient.__new__(SiteRegisterClient)
    client.uses_sitedaemon = False
    client.gnrdaemon_proxy = FakeDaemon()
    client.site = type('Site', (), {'currentDomainIdentifier': 'test'})()
    client.storage_path = 'store.pik'

    assert client.resolveSiteRegisterUris() == ('main', NEW_TEST_URI)
