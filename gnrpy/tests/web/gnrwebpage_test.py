import io
import pickle
from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.datastructures import FileStorage, MultiDict

from gnr.core.gnrlang import GnrException
from gnr.web.gnrwebpage import GnrWebPage


class _PaneStub(object):
    def __init__(self):
        self.captured = None

    def contentPane(self, **kwargs):
        self.captured = kwargs
        return self


class _PageStub(object):
    def bf_value(self, box, **kwargs):
        return box


def test_bagFieldDispatcher_without_resource_does_not_raise():
    """resource=None must not raise UnboundLocalError on mixinedClass (#1101)."""
    page = _PageStub()
    pane = _PaneStub()
    GnrWebPage.bagFieldDispatcher(page, pane, resource=None, field='value')
    assert pane.captured['bagfieldmodule'] is None


class _ApplicationStub(object):
    localizer = None


class _ExceptionPageStub(object):
    user = 'tester'
    application = _ApplicationStub()


def test_exception_unknown_name_raises_naming_it():
    """An unregistered name raises GnrException naming it, not TypeError (#1622)."""
    with pytest.raises(GnrException) as excinfo:
        GnrWebPage.exception(_ExceptionPageStub(), 'no_such_name')
    assert 'no_such_name' in str(excinfo.value)


def test_exception_registered_name_returns_instance():
    exc = GnrWebPage.exception(_ExceptionPageStub(), 'generic')
    assert isinstance(exc, GnrException)


class _ForbiddenPageStub(object):
    def __init__(self, path_info, redirect, pageArgs=None):
        self.request = type('Request', (), {'path_info': path_info})()
        self.forbiddenRedirectPage = redirect
        self.pageArgs = pageArgs or {}


def _forbidden_from(url):
    return parse_qs(urlsplit(url).query)['_forbidden_from'][0].split(',')


def test_forbiddenRedirectUrl_first_hop_marks_rejected_page():
    page = _ForbiddenPageStub('/app/other', '/app/home', {'x': '1'})
    url = GnrWebPage._forbiddenRedirectUrl(page)
    assert urlsplit(url).path == '/app/home'
    assert parse_qs(urlsplit(url).query)['x'] == ['1']
    assert _forbidden_from(url) == ['/app/other']


def test_forbiddenRedirectUrl_refuses_redirect_to_itself():
    page = _ForbiddenPageStub('/app/home', '/app/home')
    assert GnrWebPage._forbiddenRedirectUrl(page) is None


def test_forbiddenRedirectUrl_refuses_bounce_back():
    page = _ForbiddenPageStub('/app/b', '/app/a', {'_forbidden_from': '/app/a'})
    assert GnrWebPage._forbiddenRedirectUrl(page) is None


def test_forbiddenRedirectUrl_follows_chain_to_new_page():
    page = _ForbiddenPageStub('/app/b', '/app/home?tab=1', {'_forbidden_from': '/app/a'})
    url = GnrWebPage._forbiddenRedirectUrl(page)
    assert url.startswith('/app/home?tab=1&')
    assert _forbidden_from(url) == ['/app/a', '/app/b']


def test_forbiddenRedirectUrl_without_target():
    page = _ForbiddenPageStub('/app/home', None)
    assert GnrWebPage._forbiddenRedirectUrl(page) is None


class _RegisterCapture(object):
    def __init__(self):
        self.data = None

    def new_page(self, page_id, page, data=None):
        self.data = data
        return dict(data=data)


class _RegisterPageStub(object):
    wsk_enabled = False

    def __init__(self, request_kwargs, files):
        self.connection = type('Connection', (), {'connection_id': 'conn_1'})()
        self.request = type('Request', (), {'files': files})()
        self.site = type('Site', (), {'register': _RegisterCapture()})()
        self._call_kwargs = dict(request_kwargs)

    def onPageRegistered(self, **kwargs):
        pass


def test_register_new_page_keeps_uploaded_files_out_of_register_data():
    """Uploaded files must not reach the pickled register payload (#1698)."""
    upload = FileStorage(stream=io.BytesIO(b'payload'), filename='scan.txt', name='file')
    request_kwargs = {'file': upload, 'q': 'x'}
    page = _RegisterPageStub(request_kwargs, MultiDict({'file': upload}))
    init_info = dict(request_kwargs=request_kwargs, request_args=())
    GnrWebPage._register_new_page(page, kwargs=request_kwargs, init_info=init_info)
    data = pickle.loads(pickle.dumps(page.site.register.data))
    assert 'file' not in data['pageArgs']
    assert data['pageArgs']['q'] == 'x'
    assert 'file' not in data['init_info']['request_kwargs']
    assert data['init_info']['request_kwargs']['q'] == 'x'
    assert request_kwargs['file'] is upload
    assert page._call_kwargs['file'] is upload
