"""Unit tests for the per-process siteregister proxy (#1081).

A Pyro proxy carries an open socket and its own request sequence counter. The
site is built before the wsgi server forks its workers, so a proxy created at
startup must never be reused by an inherited process: two processes counting
requests on one socket read each other's replies and blow up with
``ProtocolError('reply sequence out of sync')``.

A real fork is not needed to test this: the pid the proxy was created in is
recorded on the client, so faking a foreign pid exercises the same path. What
matters just as much is *how* the inherited connection is given up, since
closing it would shut the socket down for the process it came from.
"""

import os

from gnr.web.daemon.siteregister_client import SiteRegisterClient
from gnr.web.gnrwsgisite_proxy.datacollector import DataCollector


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeSocket:
    """Wraps a real file descriptor, so os.close() has something to act on."""

    def __init__(self):
        read_fd, self.write_fd = os.pipe()
        self.fd = read_fd
        self.detached = False
        self.shutdown_called = False
        self.closed = False

    def detach(self):
        self.detached = True
        fd, self.fd = self.fd, -1
        return fd

    def shutdown(self, how):
        self.shutdown_called = True

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self):
        self.sock = _FakeSocket()
        self.keep_open = False

    def close(self):
        if self.keep_open:
            return
        self.sock.shutdown(0)
        self.sock.close()


class _FakeProxy:
    def __init__(self, uri, connected=True):
        self.uri = uri
        self._pyroConnection = _FakeConnection() if connected else None
        self.released = False

    def _pyroRelease(self):
        self.released = True
        if self._pyroConnection is not None:
            self._pyroConnection.close()
            self._pyroConnection = None


def _client(connected=True):
    """A SiteRegisterClient with its Pyro plumbing faked out.

    __init__ needs a live gnrdaemon, so it is bypassed: these tests are about
    proxy ownership, nothing else.
    """
    client = SiteRegisterClient.__new__(SiteRegisterClient)
    client.siteregister_uri = 'PYRO:SiteRegister@localhost:40000'
    client.hmac_key = b'secret'
    client.pyroProxy = lambda url: _FakeProxy(url, connected=connected)
    client.newSiteRegisterProxy()
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_same_process_keeps_its_proxy():
    client = _client()
    proxy = client.siteregister
    assert client.siteregister is proxy
    assert not proxy.released


def test_inherited_proxy_is_replaced():
    client = _client()
    inherited = client.siteregister
    client._siteregister_pid = os.getpid() + 1  # as seen by a forked worker

    fresh = client.siteregister
    assert fresh is not inherited
    assert client._siteregister_pid == os.getpid()
    assert client.siteregister is fresh  # and the replacement is kept


def test_inherited_connection_is_detached_not_shut_down():
    client = _client()
    inherited = client.siteregister
    connection = inherited._pyroConnection
    sock = connection.sock

    client._siteregister_pid = os.getpid() + 1
    client.siteregister

    assert sock.detached  # this process' descriptor is gone...
    assert not sock.shutdown_called  # ...without tearing down the shared socket
    assert not inherited.released
    assert inherited._pyroConnection is None
    # keep_open guards the socket against a late garbage collection too
    assert connection.keep_open
    connection.close()
    assert not sock.shutdown_called


def test_a_disconnected_inherited_proxy_is_replaced_too():
    client = _client(connected=False)
    inherited = client.siteregister
    client._siteregister_pid = os.getpid() + 1

    assert client.siteregister is not inherited


def test_an_assigned_proxy_belongs_to_the_assigning_process():
    """Assignment stays supported, and stamps the pid like a freshly built proxy."""
    client = _client()
    injected = _FakeProxy('PYRO:SiteRegister@elsewhere:40000')
    client.siteregister = injected

    assert client.siteregister is injected
    client._siteregister_pid = os.getpid() + 1
    assert client.siteregister is not injected


def test_datacollector_does_not_pin_the_startup_proxy():
    """DataCollector is built with the site, i.e. before the fork."""
    client = _client()
    collector = DataCollector(client)
    startup_proxy = client.siteregister
    assert collector._r is startup_proxy

    client._siteregister_pid = os.getpid() + 1
    assert collector._r is not startup_proxy
    assert collector._r is client.siteregister
