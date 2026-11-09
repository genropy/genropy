"""A method name may ask for a component to be mixed in (``pkg|path;method``).

Without a session only the components this page has already mixed in are
accepted, from the page store or from the current request, in the same
package; a logged user keeps the previous behaviour. The websocket goes
through the same rule.
"""
import types

from gnr.web.gnrwebpage import AUTH_OK, GnrWebPage
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader

LOGIN = (('login:LoginComponent',), ())


class _Page(object):
    """The slice of a page the mixin request reads; mixed records what gets mixed in."""
    _mixinRequestedComponent = GnrWebPage._mixinRequestedComponent
    _mixedByPage = GnrWebPage._mixedByPage
    getWsMethod = GnrWebPage.getWsMethod

    def _checkAuth(self, method=None, **kwargs):
        return AUTH_OK

    def __init__(self, user=None, stored=None, current=None):
        self.connection = types.SimpleNamespace(loggedUser=user)
        self._stored = set(stored or ())
        if current is not None:
            self.mixin_set = set(current)
        self.mixed = []

    def pageStore(self):
        return types.SimpleNamespace(getItem=lambda key: self._stored if key == 'mixin_set' else None)

    def mixinComponent(self, *path, **kwargs):
        self.mixed.append(path)


class _Loader(object):
    """The real mixinPageComponent, with a component that needs no resource on disk."""
    mixinPageComponent = ResourceLoader.mixinPageComponent

    def loadResource(self, *path, **kwargs):
        return types.SimpleNamespace()


class _MixinTarget(object):
    envelope_css_requires = {}
    envelope_js_requires = {}
    css_requires = []
    js_requires = []

    def mixin(self, component, **kwargs):
        pass


def test_unknown_component_without_session_is_refused():
    page = _Page(stored=[LOGIN])
    assert page._mixinRequestedComponent('*|other:Component;anyMethod') is None
    assert page.mixed == []


def test_component_mixed_by_the_page_is_accepted():
    page = _Page(stored=[LOGIN])
    assert page._mixinRequestedComponent('*|login:LoginComponent;login_checkAvatar') == 'login_checkAvatar'
    assert page.mixed == [('login:LoginComponent',)]


def test_component_mixed_in_this_request_is_accepted():
    page = _Page(current=[(('tables', 'user', 'th_user:Form'), (('pkg', 'adm'),))])
    assert page._mixinRequestedComponent('adm|tables/user/th_user:Form;anyMethod') == 'anyMethod'


def test_same_path_in_another_package_is_refused():
    page = _Page(current=[(('tables', 'user', 'th_user:Form'), (('pkg', 'adm'),))])
    assert page._mixinRequestedComponent('otherpkg|tables/user/th_user:Form;anyMethod') is None
    assert page._mixinRequestedComponent('*|tables/user/th_user:Form;anyMethod') is None
    assert page.mixed == []


def test_an_entry_without_package_matches_only_no_package():
    page = _Page(stored=[LOGIN])
    assert page._mixinRequestedComponent('adm|login:LoginComponent;login_checkAvatar') is None
    assert page._mixinRequestedComponent('*|login:LoginComponent;login_checkAvatar') == 'login_checkAvatar'


def test_mixin_set_records_the_package():
    page = _MixinTarget()
    _Loader().mixinPageComponent(page, 'tables', 'user', 'th_user:Form', pkg='adm')
    _Loader().mixinPageComponent(page, 'login:LoginComponent')
    assert page.mixin_set == {(('tables', 'user', 'th_user:Form'), (('pkg', 'adm'),)), LOGIN}


def _mixed_as_one_string(**kwargs):
    target = _MixinTarget()
    _Loader().mixinPageComponent(target, 'th/th:TableHandler', **kwargs)
    return _Page(current=target.mixin_set)


def test_a_path_mixed_in_as_one_string_is_accepted():
    page = _mixed_as_one_string()
    assert page._mixinRequestedComponent('*|th/th:TableHandler;th_method') == 'th_method'
    assert page.mixed == [('th', 'th:TableHandler')]


def test_a_path_mixed_in_as_one_string_keeps_its_package():
    page = _mixed_as_one_string(pkg='adm')
    assert page._mixinRequestedComponent('*|th/th:TableHandler;th_method') is None
    assert page._mixinRequestedComponent('adm|th/th:TableHandler;th_method') == 'th_method'


def test_websocket_without_session_refuses_an_unknown_component():
    page = _Page(stored=[LOGIN])
    assert page.getWsMethod('*|other:Component;anyMethod') is None
    assert page.mixed == []


def test_logged_user_is_unchanged():
    page = _Page(user='someone')
    assert page._mixinRequestedComponent('*|other:Component;anyMethod') == 'anyMethod'
    assert page.mixed == [('other:Component',)]
