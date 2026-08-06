"""Regression tests for GnrWsgiSite.setResultInResponse (#1032).

A page or rpc method returning a Bag is normal Genropy convention. Bag
defines __call__, so it used to pass the bare ``callable(result)`` check
in setResultInResponse and be handed back as if it were a WSGI
application, then invoked downstream as ``response(environ,
start_response)`` -- raising a TypeError, since Bag.__call__ only
accepts 0 or 1 argument.

These tests pin the branch order of setResultInResponse using real
objects (a real Bag, a real werkzeug Response, a real werkzeug
HTTPException), calling the method unbound on a light fake site, in
the same style as gnrwsgisite_folder_cleanup_test.py.
"""

from werkzeug.exceptions import Forbidden
from werkzeug.wrappers import Response

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrbag import Bag


class _FakeSite:
    """setResultInResponse does not touch self, so an empty stand-in
    is enough to call it unbound."""
    pass


def test_bag_result_returns_response_not_bag():
    """A Bag returned by a page must not be mistaken for a WSGI response."""
    bag = Bag()
    response = Response()
    result = gws.GnrWsgiSite.setResultInResponse(
        _FakeSite(), bag, response, info_kwargs={})
    assert result is response
    assert result is not bag


def test_str_result_sets_response_data():
    response = Response()
    result = gws.GnrWsgiSite.setResultInResponse(
        _FakeSite(), 'hello', response, info_kwargs={})
    assert result is response
    assert result.get_data(as_text=True) == 'hello'
    assert result.mimetype == 'text/plain'


def test_bytes_result_sets_response_data():
    response = Response()
    result = gws.GnrWsgiSite.setResultInResponse(
        _FakeSite(), b'hello', response, info_kwargs={})
    assert result is response
    assert result.get_data() == b'hello'


def test_werkzeug_response_result_replaces_response():
    response = Response()
    new_response = Response('replaced')
    result = gws.GnrWsgiSite.setResultInResponse(
        _FakeSite(), new_response, response, info_kwargs={})
    assert result is new_response
    assert result is not response


def test_wsgi_callable_result_is_still_returned():
    """A genuine WSGI callable (e.g. a werkzeug HTTPException instance,
    as returned by GnrWsgiSite.forbidden_exception/site templates on a
    caught HTTPException) must still pass through this branch."""
    response = Response()
    exc = Forbidden()
    result = gws.GnrWsgiSite.setResultInResponse(
        _FakeSite(), exc, response, info_kwargs={})
    assert result is exc
