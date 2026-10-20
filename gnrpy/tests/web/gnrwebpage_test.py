import io
import os
import pickle
from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.datastructures import FileStorage, MultiDict

from gnr.core.gnrlang import GnrException
from gnr.web.gnrwebpage import GnrWebPage, UNSET_COLOR_VARIANT


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
    wsk_enabled = True

    def __init__(self, request_kwargs, files):
        self.async_registration = None
        self.connection = type('Connection', (), {'connection_id': 'conn_1'})()
        self.request = type('Request', (), {'files': files})()
        self.site = type('Site', (), {'register': _RegisterCapture()})()
        self._call_kwargs = dict(request_kwargs)

    def registerToAsyncServer(self, **kwargs):
        self.async_registration = kwargs

    def onPageRegistered(self, **kwargs):
        pass


def test_register_new_page_keeps_uploaded_files_out_of_register_data():
    """Uploaded files must not reach the pickled register payload (#1698)."""
    upload = FileStorage(stream=io.BytesIO(b'payload'), filename='scan.txt', name='file')
    request_kwargs = {'file': upload, 'q': 'x'}
    page = _RegisterPageStub(request_kwargs, MultiDict({'file': upload}))
    init_info = dict(request_kwargs=request_kwargs, request_args=())
    class_info = dict(basepath='/app/pages', relpath='upload.py', pkg=None,
                      request_args=(), request_kwargs=request_kwargs)
    GnrWebPage._register_new_page(page, kwargs=request_kwargs,
                                  class_info=class_info, init_info=init_info)
    data = pickle.loads(pickle.dumps(page.site.register.data))
    assert 'file' not in data['class_info']['request_kwargs']
    assert data['class_info']['request_kwargs']['q'] == 'x'
    assert class_info['request_kwargs'] is request_kwargs
    assert 'file' not in data['pageArgs']
    assert data['pageArgs']['q'] == 'x'
    assert 'file' not in data['init_info']['request_kwargs']
    assert data['init_info']['request_kwargs']['q'] == 'x'
    assert request_kwargs['file'] is upload
    assert page._call_kwargs['file'] is upload
    async_registration = pickle.loads(pickle.dumps(page.async_registration))
    assert 'file' not in async_registration['class_info']['request_kwargs']
    assert 'file' not in async_registration['init_info']['request_kwargs']
    assert 'file' not in async_registration['page_info']['_call_kwargs']


class _LocalNode(object):
    def __init__(self, path):
        self.path = path
        self.exists = os.path.exists(path)

    def open(self, mode):
        return open(self.path, mode)


class _ColorVariantPageStub(object):
    resourceDirs = ()

    def __init__(self, css_files):
        loader = type('Loader', (), {'getResourceList': lambda s, dirs, path, ext: [
            f for f in css_files if f.endswith(path + '.' + ext)]})()
        self.site = type('Site', (), {'resource_loader': loader,
                                      'storageNode': staticmethod(_LocalNode)})()

    def get_css_theme(self):
        return 'mimi'

    def get_css_theme_variant(self):
        return 'base'

    def localize(self, txt):
        return txt.replace('!![en]', '')


THEMES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'resources', 'common', 'themes')


def _color_variants(css_files, **kwargs):
    return GnrWebPage.getAvailableColorVariants(_ColorVariantPageStub(css_files), **kwargs).split(',')


def test_color_variants_theme_option_merges_gray_into_default():
    """The theme default entry stands for gray, which leaves the list."""
    css_files = [os.path.join(THEMES_DIR, 'mimi.css'), os.path.join(THEMES_DIR, 'mimi', 'base.css')]
    assert 'gray' in _color_variants(css_files)
    variants = _color_variants(css_files, unset_option='theme')
    assert variants[0] == f'{UNSET_COLOR_VARIANT}:Gray (default)'
    assert 'gray' not in variants
    assert 'blue' in variants


def test_color_variants_theme_option_without_gray(tmp_path):
    css = tmp_path / 'themes' / 'plain.css'
    css.parent.mkdir()
    css.write_text('body.color_variant_red {color: red;}\n')
    variants = _color_variants([str(css)], theme='plain', unset_option='theme')
    assert variants == [f'{UNSET_COLOR_VARIANT}:Default', 'red']


def test_color_variants_application_option_keeps_gray():
    css_files = [os.path.join(THEMES_DIR, 'mimi.css')]
    variants = _color_variants(css_files, unset_option='application')
    assert variants[0] == f'{UNSET_COLOR_VARIANT}:Application default'
    assert 'gray' in variants
