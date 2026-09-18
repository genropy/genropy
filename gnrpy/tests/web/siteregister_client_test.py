"""Tests for the Pyro proxies the site register client talks to the daemon with.

No daemon is involved: the proxies are never connected, `Proxy._pyroInvoke` is
replaced with a stub so the retry behaviour can be observed on its own.
"""

import Pyro4
import pytest

from gnr.web.daemon.siteregister import MAX_RETRY_ATTEMPTS, OLD_HMAC_MODE
from gnr.web.daemon.siteregister_client import SiteRegisterClient, build_proxy

TEST_URI = 'PYRO:SiteRegister@localhost:40000'


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
