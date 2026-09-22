"""getSelection resolves a saved query before deriving limit and wherebag.

A saved query used to be loaded after the prologue had already applied the
hardQueryLimit fallback and derived the WHERE bag, so its empty queryLimit
dropped the instance limit and its WHERE never reached whereAsPlainText.

The database is real: the ``test_invoice`` project on postgres, with the CSV
data of projects/test_invoice/data/export imported by the same loader the sql
suite uses, and real adm.userobject records.  Postgres is mandatory here:
adm.userobject carries formula columns built on ``string_to_array``, which
sqlite does not have, so ``loadUserObject`` cannot run there.  Only the HTTP
page context is replaced by a stand-in, because the suite has no
infrastructure that produces a live GnrWebPage.
"""

import os

import pytest

from core.common import BaseGnrTest
from sql.conftest import _db_pg

from gnr.core.gnrbag import Bag
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler


NSW_CUSTOMERS = 399


class _MemoryStore:
    """In memory replacement for the daemon backed page/user store."""

    def __init__(self):
        self.data = Bag()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return False

    def getItem(self, path, default=None, **kwargs):
        value = self.data[path]
        return default if value is None else value

    def setItem(self, path, value=None, **kwargs):
        self.data.setItem(path, value)

    def popNode(self, path, **kwargs):
        return self.data.popNode(path)


class _StandInRegister:
    """No page is registered: every slave selection lookup finds nothing."""

    def exists(self, page_id, register_name=None):
        return False


class _StandInSite:
    def __init__(self, gnrapp):
        self.gnrapp = gnrapp
        self.register = _StandInRegister()


class _StandInPage:
    """The page services of the getSelection flow, and nothing more.

    Freezing is not reimplemented: the freeze methods call the real
    GnrBaseWebPage implementations unbound, as _gnrbasewebpage_test.py does.
    """

    def __init__(self, db, connectionFolder, page_id='test_page'):
        self.db = db
        self.connectionFolder = connectionFolder
        self.page_id = page_id
        self.locale = 'en'
        self.user = 'admin'
        self.avatar = None
        self.site = _StandInSite(db.application)
        self.rpc_methods = {}
        self.published = []
        self._event_subscribers = {}
        self._page_store = _MemoryStore()
        self._user_store = _MemoryStore()

    def _subscribe_event(self, event, caller):
        self._event_subscribers.setdefault(event, []).append(caller)

    @property
    def application(self):
        return self.site.gnrapp

    @property
    def permissionPars(self):
        return dict(user=self.user, user_group=None)

    def pageStore(self, page_id=None, triggered=True):
        return self._page_store

    def userStore(self, user=None, triggered=True):
        return self._user_store

    def getPublicMethod(self, prefix, method):
        if callable(method):
            return method
        return self.rpc_methods.get(method)

    def clientPublish(self, topic, **kwargs):
        self.published.append((topic, kwargs))

    def pageLocalDocument(self, docname, page_id=None):
        return GnrBaseWebPage.pageLocalDocument(self, docname, page_id=page_id)

    def freezeSelection(self, selection, name, **kwargs):
        return GnrBaseWebPage.freezeSelection(self, selection, name, **kwargs)

    def freezeSelectionUpdate(self, selection):
        return GnrBaseWebPage.freezeSelectionUpdate(self, selection)

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        return GnrBaseWebPage.unfreezeSelection(self, dbtable=dbtable, name=name,
                                                page_id=page_id)

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        return GnrBaseWebPage.freezedPkeys(self, dbtable=dbtable, name=name,
                                           page_id=page_id)


@pytest.fixture(scope='module')
def gnr_test_config():
    """A genro configuration for the module, as tests/sql/conftest.py does."""
    if os.environ.get('GENRO_GNRFOLDER'):
        yield
        return
    BaseGnrTest.setup_class()
    try:
        yield
    finally:
        BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def db_postgres(request, gnr_test_config):
    yield from _db_pg(request, 'postgres')


@pytest.fixture
def handler(db_postgres, tmp_path):
    return GnrWebAppHandler(_StandInPage(db_postgres, str(tmp_path)))


def _customer_where_bag():
    wherebag = Bag()
    wherebag.setItem('c_1', 'NSW', column='state', op='equal')
    return wherebag


def _new_userobject(db, code, objtype, data):
    tblobj = db.table('adm.userobject')
    record = tblobj.newrecord(code=code, objtype=objtype, pkg='invc',
                              tbl='invc.customer', data=data)
    tblobj.insert(record)
    db.commit()
    return record['id']


@pytest.fixture(scope='module')
def unlimited_saved_query(db_postgres):
    """A saved query with a WHERE and no queryLimit, as the query tool saves it."""
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = None
    return _new_userobject(db_postgres, 'unlimited_saved_query', 'query', data)


def _rows(result):
    data, _ = result
    return [(node.label, dict(node.attr)) for node in data]


def test_saved_query_without_limit_honours_hard_query_limit(handler, db_postgres,
                                                            unlimited_saved_query):
    """The instance limit must survive a saved query whose queryLimit is empty."""
    assert db_postgres.table('invc.customer').query(
        columns='$id', where='$state=:st', st='NSW').count() == NSW_CUSTOMERS
    result = handler.getSelection(table='invc.customer',
                                  columns='$account_name,$state',
                                  savedQuery=unlimited_saved_query,
                                  order_by='$account_name',
                                  hardQueryLimit=5)
    rows = _rows(result)
    attrs = result[1]
    assert len(rows) == 5
    assert {row[1]['state'] for row in rows} == {'NSW'}
    assert attrs['totalrows'] == 5
    assert attrs['hardQueryLimitOver'] is True


def test_saved_query_under_hard_query_limit_does_not_signal_overflow(handler,
                                                                     unlimited_saved_query):
    """A limit above the matching rows leaves hardQueryLimitOver false."""
    result = handler.getSelection(table='invc.customer',
                                  columns='$account_name,$state',
                                  savedQuery=unlimited_saved_query,
                                  order_by='$account_name',
                                  hardQueryLimit=NSW_CUSTOMERS + 10)
    attrs = result[1]
    assert attrs['totalrows'] == NSW_CUSTOMERS
    assert attrs['hardQueryLimitOver'] is False


def test_saved_query_produces_where_as_plain_text(handler, unlimited_saved_query):
    """The saved WHERE must reach the plain text description of the filter."""
    result = handler.getSelection(table='invc.customer',
                                  columns='$account_name,$state',
                                  savedQuery=unlimited_saved_query,
                                  order_by='$account_name',
                                  hardQueryLimit=5)
    attrs = result[1]
    assert attrs.get('whereAsPlainText')
    assert 'NSW' in attrs['whereAsPlainText']


def test_saved_query_with_own_limit_still_wins(handler, db_postgres):
    """A saved queryLimit keeps precedence over the instance limit."""
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = 3
    query_id = _new_userobject(db_postgres, 'limited_saved_query', 'query', data)
    result = handler.getSelection(table='invc.customer',
                                  columns='$account_name,$state',
                                  savedQuery=query_id,
                                  order_by='$account_name',
                                  hardQueryLimit=50)
    assert len(_rows(result)) == 3
