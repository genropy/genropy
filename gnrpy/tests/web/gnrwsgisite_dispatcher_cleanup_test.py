"""Regression test for the thread-local cleanup at the end of
``GnrWsgiSite.dispatcher()`` (#379/#380).

``dispatcher()`` sets ``currentRequest``/``currentDomain`` for the
serving thread and, in its ``finally`` block, calls ``cleanup()`` to pop
every thread-local slot again. The real properties involved
(``currentPage``, ``currentRequest``, ``currentAuxInstanceName``,
``currentDomain``) are backed by ``gnr.core.gnrlang.ThreadedDict``,
where assigning ``None`` pops the current thread's entry. The fake site
below reuses those exact property/method objects from ``GnrWsgiSite``
so the test exercises the real pop semantics, not a mock of them; only
the pieces external to this mechanism (``_dispatcher``, ``errorHandler``,
``db``) are faked.
"""

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrlang import ThreadedDict
from werkzeug.test import EnvironBuilder


class _FakeDb:
    def closeConnection(self):
        pass


class _FakeSite:
    """Reuses the real thread-local properties and cleanup()/
    raiseIfDeveloper() from GnrWsgiSite, so dispatcher() (called unbound)
    exercises the actual pop-on-None behaviour instead of a mock of it.
    """

    currentPage = gws.GnrWsgiSite.currentPage
    currentRequest = gws.GnrWsgiSite.currentRequest
    currentAuxInstanceName = gws.GnrWsgiSite.currentAuxInstanceName
    currentDomain = gws.GnrWsgiSite.currentDomain
    cleanup = gws.GnrWsgiSite.cleanup
    raiseIfDeveloper = gws.GnrWsgiSite.raiseIfDeveloper

    def __init__(self, dispatcher_exc=None):
        self._currentPages = ThreadedDict()
        self._currentRequests = ThreadedDict()
        self._currentAuxInstanceNames = ThreadedDict()
        self._currentDomains = ThreadedDict()
        self.rootDomain = '_main_'
        self.debug = False
        self.db = _FakeDb()
        self.errorHandler_calls = []
        self._dispatcher_exc = dispatcher_exc

    def _dispatcher(self, environ, start_response):
        if self._dispatcher_exc is not None:
            raise self._dispatcher_exc
        return [b'ok']

    def errorHandler(self, exception=None, traceback=None):
        self.errorHandler_calls.append(exception)


def _wsgi_environ():
    return EnvironBuilder(path='/some/page').get_environ()


def _start_response(status, headers):
    pass


def test_dispatcher_success_leaves_no_thread_local_residue():
    """Happy path: cleanup() still pops every slot after a normal
    return, no thread-local entry survives the request."""
    site = _FakeSite()
    environ = _wsgi_environ()

    gws.GnrWsgiSite.dispatcher(site, environ, _start_response)

    assert site._currentRequests._data == {}
    assert site._currentDomains._data == {}
    assert site._currentPages._data == {}
    assert site._currentAuxInstanceNames._data == {}


def test_dispatcher_exception_leaves_no_thread_local_residue():
    """Error path: _dispatcher raises, the except branch builds a 500
    response, and the finally block must still leave every thread-local
    slot empty. Before the #380 fix this passed too because cleanup()
    already popped currentDomain; the residual line then re-added a
    never-removed {tid: '_main_'} entry, which this test would catch if
    that line came back."""
    site = _FakeSite(dispatcher_exc=RuntimeError('boom'))
    environ = _wsgi_environ()

    gws.GnrWsgiSite.dispatcher(site, environ, _start_response)

    assert len(site.errorHandler_calls) == 1
    assert site._currentRequests._data == {}
    assert site._currentDomains._data == {}
    assert site._currentPages._data == {}
    assert site._currentAuxInstanceNames._data == {}


def test_dispatcher_currentdomain_falls_back_to_rootdomain_after_cleanup():
    """After the request is done, reading currentDomain again (e.g. from
    another request on the same thread) must still see rootDomain via
    the property's fallback, not a stale per-thread value."""
    site = _FakeSite(dispatcher_exc=RuntimeError('boom'))
    environ = _wsgi_environ()

    gws.GnrWsgiSite.dispatcher(site, environ, _start_response)

    assert site.currentDomain == site.rootDomain
