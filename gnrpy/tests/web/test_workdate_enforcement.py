"""Workdate enforcement on the server (#1377).

The login rootenv comes from the client, whose clock may be wrong or in
another time zone. Without the workdate capability the workdate must be the
server's today whatever the client sent, and neither ``_workdate`` on the URL
nor ``setWorkdate`` may move it. With the capability the current behaviour
stays.

The login component is loaded by path: ``projects/`` is not importable.
"""
import datetime
import importlib.util
import pathlib
import types

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from gnr.web.gnrwebpage import GnrWebPage

LOGIN = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore'
         / 'packages' / 'adm' / 'resources' / 'login.py')

TODAY = datetime.date.today()
TWO_DAYS_AHEAD = -2 * 86400 * 1000
THREE_HOURS_BEHIND = 3 * 3600 * 1000


def _login_component():
    spec = importlib.util.spec_from_file_location('adm_login', LOGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LoginComponent


class _Application(object):
    checkResourcePermission = GnrApp.checkResourcePermission


class _Page(object):
    """The slice of the login page the workdate code touches."""
    auth_workdate = 'admin'

    def __init__(self, user_tags, rootenv=None):
        self.application = _Application()
        self.avatar = types.SimpleNamespace(user_tags=user_tags)
        self.user = 'someone'
        self.rootenv = rootenv if rootenv is not None else Bag()
        self.workdate = TODAY
        self._call_kwargs = {}
        self._workdate_set = None

    def pageAuthTags(self, method=None):
        return getattr(self, 'auth_%s' % method, None)

    clientDatetime = GnrWebPage.clientDatetime


def _component(user_tags, **kw):
    cls = _login_component()
    page = _Page(user_tags, **kw)
    page.login_canSetWorkdate = types.MethodType(cls.login_canSetWorkdate, page)
    page.login_enforceWorkdate = types.MethodType(cls.login_enforceWorkdate, page)
    return page


def _client_default(page, delta):
    return page.clientDatetime(serverTimeDelta=delta).date()


@pytest.mark.parametrize('delta', [TWO_DAYS_AHEAD, THREE_HOURS_BEHIND])
def test_without_capability_workdate_is_server_today(delta):
    page = _component('user')
    rootenv = Bag(dict(workdate=_client_default(page, delta), login_date=TODAY))
    page.login_enforceWorkdate(rootenv)
    assert rootenv['can_set_workdate'] is False
    assert rootenv['workdate'] == TODAY
    assert rootenv['login_date'] == TODAY
    assert rootenv['custom_workdate'] is False


def test_with_capability_client_workdate_is_kept():
    page = _component('admin,user')
    client_date = _client_default(page, TWO_DAYS_AHEAD)
    rootenv = Bag(dict(workdate=client_date, login_date=TODAY))
    page.login_enforceWorkdate(rootenv)
    assert rootenv['can_set_workdate'] is True
    assert rootenv['workdate'] == client_date
    assert rootenv['custom_workdate'] is (client_date != TODAY)


def test_client_flag_in_rootenv_is_not_trusted():
    page = _component('user')
    rootenv = Bag(dict(workdate=TODAY + datetime.timedelta(days=2), login_date=TODAY,
                       can_set_workdate=True))
    page.login_enforceWorkdate(rootenv)
    assert rootenv['can_set_workdate'] is False
    assert rootenv['workdate'] == TODAY


def test_url_workdate_ignored_without_capability():
    rootenv = Bag(dict(workdate=TODAY, can_set_workdate=False))
    page = _Page('user', rootenv=rootenv)
    page._call_kwargs = {'_workdate': '2026-09-23'}
    page.root_page_id = None
    page.parent_page_id = None
    page.page_id = 'p1'
    page.pageStore = lambda page_id=None: types.SimpleNamespace(getItem=lambda k: None)
    page.connectionStore = lambda: types.SimpleNamespace(getItem=lambda k: rootenv)
    page.catalog = types.SimpleNamespace(fromText=lambda v, t: datetime.date.fromisoformat(v))
    result = GnrWebPage.getStartRootenv(page)
    assert result['workdate'] == TODAY


def test_url_workdate_applied_with_capability():
    rootenv = Bag(dict(workdate=TODAY, can_set_workdate=True))
    page = _Page('admin', rootenv=rootenv)
    page._call_kwargs = {'_workdate': '2026-09-23'}
    page.root_page_id = None
    page.parent_page_id = None
    page.page_id = 'p1'
    page.pageStore = lambda page_id=None: types.SimpleNamespace(getItem=lambda k: None)
    page.connectionStore = lambda: types.SimpleNamespace(getItem=lambda k: rootenv)
    page.catalog = types.SimpleNamespace(fromText=lambda v, t: datetime.date.fromisoformat(v))
    result = GnrWebPage.getStartRootenv(page)
    assert result['workdate'] == datetime.date(2026, 9, 23)


def test_setWorkdate_refused_without_capability():
    page = _Page('user', rootenv=Bag(dict(can_set_workdate=False)))
    with pytest.raises(GnrException):
        GnrWebPage.setWorkdate(page, workdate=TODAY + datetime.timedelta(days=2))
    assert page.workdate == TODAY


def test_setWorkdate_refused_without_rootenv():
    page = _Page('user', rootenv=None)
    page.rootenv = None
    with pytest.raises(GnrException):
        GnrWebPage.setWorkdate(page, workdate=TODAY + datetime.timedelta(days=2))


def test_setWorkdate_allowed_with_capability():
    page = _Page('admin', rootenv=Bag(dict(can_set_workdate=True)))
    target = TODAY + datetime.timedelta(days=2)
    assert GnrWebPage.setWorkdate(page, workdate=target) == target
