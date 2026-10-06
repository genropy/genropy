from urllib.parse import parse_qs, urlsplit

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
