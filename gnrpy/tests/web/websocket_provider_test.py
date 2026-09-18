"""Coverage for the optional ``gnr.web:websockethandler`` selection.

The WebSocket interface of a provider is optional where the register is not.
``gnr.web.daemon`` refuses to start when ``GNR_DAEMON_PROVIDER`` names a
provider whose register it cannot find, because the register is what the
process needs; a provider that terminates no socket declares no
``websockethandler`` and the site keeps the classic handler — and with it the
classic probe, which finds no ``async.sock`` and turns the site's WebSockets
off. That difference is what these tests hold in place: an HTTP-only provider
must start.
"""
import importlib.metadata
from types import SimpleNamespace

import pytest

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web.gnrdummysite import GnrDummySite
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwsgisite_proxy import gnrwebsockethandler as handler_module
from gnr.web.gnrwsgisite_proxy.gnrwebsockethandler import (WsgiWebSocketHandler,
                                                          websocketHandlerClass)

PROVIDER_ENV = handler_module.DAEMON_PROVIDER_ENV
PROVIDER_MODULE = 'gnr.web.gnrwsgisite_proxy.gnrwebsockethandler'
PROVIDER_DIST = 'websocket-test-provider'
OTHER_DIST = 'another-test-provider'


class FakeWebSocketHandler(object):
    """What a provider declares: a class built with the site, and two methods."""
    client_module = 'gnrwebsocket_wsx'

    def __init__(self, site):
        self.site = site

    def checkSocket(self):
        return True

    def sendCommandToPage(self, page_id, command, data):
        pass


NotAClass = object()


class HandlerWithoutSendCommand(object):
    def checkSocket(self):
        return True


def entry_point(value, dist_name):
    """A real ``EntryPoint``, so ``.module`` is derived and not asserted.

    ``.module`` strips the ``:attr`` suffix the spec allows; a stub declaring
    both fields by hand would agree with whatever the code happens to read.
    """
    ep = importlib.metadata.EntryPoint(
        name=handler_module.WEBSOCKET_ENTRY_POINT_NAME, value=value,
        group=handler_module.WEBSOCKET_ENTRY_POINT_GROUP)
    object.__setattr__(ep, 'dist', SimpleNamespace(name=dist_name))
    return ep


@pytest.fixture
def declared(monkeypatch):
    """Publish entry points for the websockethandler name, and nothing else."""
    def declare(*eps):
        def fake_entry_points(**kwargs):
            wanted = (handler_module.WEBSOCKET_ENTRY_POINT_GROUP,
                      handler_module.WEBSOCKET_ENTRY_POINT_NAME)
            if (kwargs.get('group'), kwargs.get('name')) == wanted:
                return list(eps)
            return []
        monkeypatch.setattr(importlib.metadata, 'entry_points', fake_entry_points)
    return declare


# --- the selection ---------------------------------------------------------

def test_without_the_variable_the_entry_points_are_never_looked_up(monkeypatch):
    """A classic install pays nothing and gets the classic handler."""
    monkeypatch.delenv(PROVIDER_ENV, raising=False)

    def forbidden(**kwargs):
        raise AssertionError('entry points were scanned without a provider')

    monkeypatch.setattr(importlib.metadata, 'entry_points', forbidden)
    assert websocketHandlerClass() is WsgiWebSocketHandler


def test_a_provider_that_declares_no_websockethandler_keeps_the_classic_one(
        monkeypatch, declared):
    """The HTTP-only provider: the register is replaced, the socket is not."""
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared()
    assert websocketHandlerClass() is WsgiWebSocketHandler


def test_another_providers_websockethandler_is_not_taken(monkeypatch, declared):
    """Only the provider that was named answers for this process."""
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared(entry_point(f'{PROVIDER_MODULE}:WsgiWebSocketHandler', OTHER_DIST))
    assert websocketHandlerClass() is WsgiWebSocketHandler


def test_the_provider_is_matched_on_its_distribution_name(monkeypatch, declared):
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared(entry_point(f'{__name__}:FakeWebSocketHandler', PROVIDER_DIST))
    assert websocketHandlerClass() is FakeWebSocketHandler


def test_the_provider_is_matched_on_its_module(monkeypatch, declared):
    monkeypatch.setenv(PROVIDER_ENV, __name__)
    declared(entry_point(f'{__name__}:FakeWebSocketHandler', PROVIDER_DIST))
    assert websocketHandlerClass() is FakeWebSocketHandler


def test_two_entry_points_for_one_provider_are_a_configuration_error(
        monkeypatch, declared):
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared(entry_point(f'{__name__}:FakeWebSocketHandler', PROVIDER_DIST),
             entry_point(f'{PROVIDER_MODULE}:WsgiWebSocketHandler', PROVIDER_DIST))
    with pytest.raises(ImportError) as failure:
        websocketHandlerClass()
    assert 'matches 2' in str(failure.value)


def test_an_entry_point_that_is_not_a_class_is_refused(monkeypatch, declared):
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared(entry_point(f'{__name__}:NotAClass', PROVIDER_DIST))
    with pytest.raises(ImportError) as failure:
        websocketHandlerClass()
    assert 'handler class' in str(failure.value)


def test_a_handler_missing_a_method_of_the_interface_is_refused(
        monkeypatch, declared):
    monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
    declared(entry_point(f'{__name__}:HandlerWithoutSendCommand', PROVIDER_DIST))
    with pytest.raises(ImportError) as failure:
        websocketHandlerClass()
    assert 'sendCommandToPage' in str(failure.value)


# --- the client the selected handler names ---------------------------------

FRONTEND_IMPORTS = ['genro', 'genro_rpc', 'gnrwebsocket', 'gnrsharedobjects']


def page_with(wsk):
    """The part of a page ``gnrjs_imports`` reads: its frontend and its wsk."""
    return SimpleNamespace(
        frontend=SimpleNamespace(gnrjs_frontend=lambda: list(FRONTEND_IMPORTS)),
        wsk=wsk)


def test_the_classic_handler_leaves_the_frontend_imports_alone():
    imports = GnrWebPage.gnrjs_imports(page_with(WsgiWebSocketHandler(
        SimpleNamespace(site_path='/tmp/no_site', instance_path='/tmp/no_site'))))
    assert imports == FRONTEND_IMPORTS


def test_a_site_without_websockets_leaves_the_frontend_imports_alone():
    assert GnrWebPage.gnrjs_imports(page_with(None)) == FRONTEND_IMPORTS


def test_the_named_client_takes_the_place_of_the_classic_one():
    imports = GnrWebPage.gnrjs_imports(page_with(FakeWebSocketHandler(None)))
    assert imports == ['genro', 'genro_rpc', 'gnrwebsocket_wsx', 'gnrsharedobjects']
    assert 'gnrwebsocket' not in imports


# --- what a real site does with the selection ------------------------------

class TestSiteWebSocketSelection(BaseGnrTest):
    """A real site on the isolated ``gnrtest`` instance, built both ways.

    The site reads the selection in ``__init__``, so every test builds its own:
    the variable and the entry points must be in place before the site exists.
    """

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()

    def build_site(self):
        return GnrDummySite(self.test_instance_name,
                            site_name=self.test_instance_name)

    def test_without_a_provider_the_site_has_no_websockets(self, monkeypatch):
        """The instance writes no ``wsgi?websockets``: nothing turns them on."""
        monkeypatch.delenv(PROVIDER_ENV, raising=False)
        site = self.build_site()
        assert site.websocket_handler_class is WsgiWebSocketHandler
        assert not site.websockets
        assert site.wsk is None

    def test_a_selected_provider_gives_the_site_its_handler(self, monkeypatch,
                                                            declared):
        """No config word, no ``async.sock`` probe: the provider says so."""
        monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
        declared(entry_point(f'{__name__}:FakeWebSocketHandler', PROVIDER_DIST))
        site = self.build_site()
        assert site.websockets is True
        assert isinstance(site.wsk, FakeWebSocketHandler)
        assert site.wsk.site is site
        assert site.wsk is site.wsk

    def test_a_http_only_provider_leaves_the_site_without_websockets(
            self, monkeypatch, declared):
        """The regression the closed precedent would have caused: it must start."""
        monkeypatch.setenv(PROVIDER_ENV, PROVIDER_DIST)
        declared()
        site = self.build_site()
        assert site.websocket_handler_class is WsgiWebSocketHandler
        assert not site.websockets
        assert site.wsk is None
