"""Equivalence between GnrWebAppHandler and GnrWebAppHandlerNext.

GnrWebAppHandlerNext moves the table level part of the getSelection flow onto
an app level table proxy (``tblobj.selectionProxy()``).  It is a pure
refactoring, so every input must give the same output through both handlers:
these tests run the same getSelection call twice, once per handler, and compare
rows, columns and resultAttributes.

The database is real: the ``test_invoice`` project on a temporary sqlite file,
with the CSV data of projects/test_invoice/data/export imported by the same
loader the sql suite uses.  Queries, selections and adm.userobject records are
real too.  Only the HTTP page context is replaced by a stand-in, because the
suite has no infrastructure that produces a live GnrWebPage: the stand-in
carries the page services the flow needs (page store, user store, freezing,
locale, permissions, rpc method lookup) and nothing else.
"""

import os
import shutil
import tempfile

import pytest

from core.common import BaseGnrTest
from sql.conftest import _db_pg, _import_csv_data

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.apphandler.next import GnrWebAppHandlerNext


# ---------------------------------------------------------------------------
#  The stand-in page
# ---------------------------------------------------------------------------

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

    Freezing is not reimplemented: the four freeze methods call the real
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

    # --- proxy machinery ---

    def _subscribe_event(self, event, caller):
        self._event_subscribers.setdefault(event, []).append(caller)

    @property
    def application(self):
        return self.site.gnrapp

    # --- page services ---

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

    # --- freezing, on the real implementations ---

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


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

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
def db(gnr_test_config):
    """The test_invoice application on a temporary sqlite database."""
    tmpdir = tempfile.mkdtemp()
    app = None
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(tmpdir, 'testing'),
        ))
        app.db.model.check(applyChanges=True)
        _import_csv_data(app.db)
        yield app.db
    finally:
        if app is not None:
            app.db.closeConnection()
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='module')
def db_postgres(request, gnr_test_config):
    """The test_invoice application on postgres.

    adm.userobject carries formula columns built on ``string_to_array``, which
    sqlite does not have, so ``loadUserObject`` — and with it every saved query
    and saved view — can only be exercised here.
    """
    yield from _db_pg(request, 'postgres')


@pytest.fixture
def make_handlers(tmp_path):
    """Build one handler of each class on a given database."""
    def build(db):
        legacy_page = _StandInPage(db, str(tmp_path / 'legacy'))
        next_page = _StandInPage(db, str(tmp_path / 'next'))
        return GnrWebAppHandler(legacy_page), GnrWebAppHandlerNext(next_page)
    return build


@pytest.fixture
def handlers(make_handlers, db):
    return make_handlers(db)


@pytest.fixture
def pg_handlers(make_handlers, db_postgres):
    return make_handlers(db_postgres)


# ---------------------------------------------------------------------------
#  Comparison helpers
# ---------------------------------------------------------------------------

VOLATILE_ATTRIBUTES = ('servertime', 'newproc')


def _normalized(result):
    data, attributes = result
    rows = [(node.label, dict(node.attr)) for node in data]
    attributes = {k: v for k, v in attributes.items()
                  if k not in VOLATILE_ATTRIBUTES}
    return rows, attributes


def _run_both(handlers, **pars):
    legacy, nxt = handlers
    return legacy.getSelection(**pars), nxt.getSelection(**pars)


def _assert_same(handlers, **pars):
    legacy_result, next_result = _run_both(handlers, **pars)
    legacy_rows, legacy_attrs = _normalized(legacy_result)
    next_rows, next_attrs = _normalized(next_result)
    assert next_rows == legacy_rows
    assert next_attrs == legacy_attrs
    return legacy_rows, legacy_attrs


def _customer_where_bag():
    wherebag = Bag()
    wherebag.setItem('c_1', 'NSW', column='state', op='equal')
    return wherebag


def _customer_view_bag():
    viewbag = Bag()
    viewbag.setItem('c_0', None, field='account_name')
    viewbag.setItem('c_1', None, field='state')
    return viewbag


def _new_userobject(db, code, objtype, data):
    tblobj = db.table('adm.userobject')
    record = tblobj.newrecord(code=code, objtype=objtype, pkg='invc',
                              tbl='invc.customer', data=data)
    tblobj.insert(record)
    db.commit()
    return record['id']


# ---------------------------------------------------------------------------
#  getSelection equivalence
# ---------------------------------------------------------------------------

def test_columns_as_string(handlers):
    rows, attrs = _assert_same(handlers, table='invc.customer',
                               columns='$account_name,$state',
                               order_by='$account_name', limit=5)
    assert rows
    assert attrs['table'] == 'invc.customer'


def test_columns_as_struct_bag(handlers):
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns=_customer_view_bag(),
                           order_by='$account_name', limit=5)
    assert rows
    assert 'account_name' in rows[0][1]


def test_where_bag(handlers):
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,$state',
                           where=_customer_where_bag(),
                           order_by='$account_name')
    assert rows
    assert {row[1]['state'] for row in rows} == {'NSW'}


def test_where_bag_whereasplaintext(handlers):
    _, attrs = _assert_same(handlers, table='invc.customer',
                            columns='$account_name,$state',
                            where=_customer_where_bag(),
                            order_by='$account_name')
    assert attrs['whereAsPlainText']


def test_condition_with_kwargs(handlers):
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,$state',
                           condition='$state = :wanted_state', wanted_state='VIC',
                           order_by='$account_name')
    assert rows
    assert {row[1]['state'] for row in rows} == {'VIC'}


def test_order_by_and_limit(handlers):
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name',
                           order_by='$account_name desc', limit=3)
    assert len(rows) == 3


def test_pkeys(handlers, db):
    pkeys = db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=3).fetch()
    pkeys = [r['id'] for r in pkeys]
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name', pkeys=pkeys)
    assert len(rows) == 3


def test_single_pkey(handlers, db):
    pkey = db.table('invc.customer').query(columns='$id', limit=1).fetch()[0]['id']
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name', pkeys=[pkey])
    assert len(rows) == 1


def test_filtering_pkeys_as_string(handlers, db):
    pkeys = [r['id'] for r in db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=4).fetch()]
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name',
                           filteringPkeys=','.join(pkeys))
    assert len(rows) == 4


def test_filtering_pkeys_single_value(handlers, db):
    pkey = db.table('invc.customer').query(columns='$id', limit=1).fetch()[0]['id']
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name', filteringPkeys=pkey)
    assert len(rows) == 1


def test_filtering_pkeys_from_rpc_method(handlers, db):
    pkeys = [r['id'] for r in db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=2).fetch()]

    def filter_method(**kwargs):
        return pkeys

    for handler in handlers:
        handler.page.rpc_methods['filter_method'] = filter_method
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name',
                           filteringPkeys='filter_method')
    assert len(rows) == 2


def test_count_only(handlers, db):
    legacy_result, next_result = _run_both(handlers, table='invc.customer',
                                           columns='$account_name',
                                           countOnly=True)
    assert next_result == legacy_result
    expected = db.table('invc.customer').query(columns='$id').count()
    assert legacy_result[1]['totalrows'] == expected


def test_sum_columns(handlers):
    _, attrs = _assert_same(handlers, table='invc.invoice',
                            columns='$inv_number,$total',
                            sum_columns='total')
    assert 'sum_total' in attrs


def test_distinct(handlers):
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$state', distinct=True,
                           order_by='$state')
    assert rows


def test_total_row_count(handlers):
    _, attrs = _assert_same(handlers, table='invc.customer',
                            columns='$account_name',
                            condition='$state = :wanted_state', wanted_state='NSW',
                            totalRowCount=True)
    assert attrs['totalRowCount'] > 0


def test_query_mode_union(handlers, db):
    """queryMode needs a frozen selection: the '*' prefix freezes without
    reusing, so the first call freezes and the second one runs the set
    operation against the frozen pkeys."""
    first = dict(table='invc.customer', columns='$account_name',
                 selectionName='*qmsel', order_by='$account_name', limit=3)
    _assert_same(handlers, **first)
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name', selectionName='*qmsel',
                           queryMode='U', order_by='$account_name', limit=5)
    assert rows


def test_query_mode_intersection(handlers):
    first = dict(table='invc.customer', columns='$account_name',
                 selectionName='*qmsel2', order_by='$account_name', limit=4)
    _assert_same(handlers, **first)
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name', selectionName='*qmsel2',
                           queryMode='I', order_by='$account_name', limit=4)
    assert rows


def test_saved_view(pg_handlers, db_postgres):
    view_id = _new_userobject(db_postgres, 'test_saved_view', 'view',
                              _customer_view_bag())
    rows, _ = _assert_same(pg_handlers, table='invc.customer', savedView=view_id,
                           order_by='$account_name', limit=5)
    assert rows
    assert 'account_name' in rows[0][1]
    assert 'state' in rows[0][1]


def test_saved_query(pg_handlers, db_postgres):
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = 5
    query_id = _new_userobject(db_postgres, 'test_saved_query', 'query', data)
    rows, _ = _assert_same(pg_handlers, table='invc.customer',
                           columns='$account_name,$state',
                           savedQuery=query_id, order_by='$account_name')
    assert rows
    assert {row[1]['state'] for row in rows} == {'NSW'}


def test_saved_query_with_view(pg_handlers, db_postgres):
    view_id = _new_userobject(db_postgres, 'test_saved_query_view', 'view',
                              _customer_view_bag())
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = 4
    data['currViewPath'] = view_id
    query_id = _new_userobject(db_postgres, 'test_saved_query_both', 'query', data)
    rows, _ = _assert_same(pg_handlers, table='invc.customer', savedQuery=query_id,
                           order_by='$account_name')
    assert rows
    assert 'account_name' in rows[0][1]


def test_join_conditions_bag(handlers):
    condition = Bag()
    condition.setItem('c_1', 'NSW', column='state', op='equal')
    jc = Bag()
    jc['relation'] = '@state'
    jc['condition'] = condition
    jc['one_one'] = True
    joinConditions = Bag()
    joinConditions['jc_1'] = jc
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,@state.name',
                           joinConditions=joinConditions,
                           order_by='$account_name', limit=5)
    assert rows


def test_structure(handlers):
    legacy_result, next_result = _run_both(handlers, table='invc.customer',
                                           columns='$account_name,$state',
                                           structure=True, limit=3)
    assert next_result[0]['structure'].toXml() == legacy_result[0]['structure'].toXml()
    assert next_result[0]['data'].toXml() == legacy_result[0]['data'].toXml()


def test_get_record_count(handlers):
    legacy, nxt = handlers
    pars = dict(table='invc.customer', where=_customer_where_bag())
    assert nxt.getRecordCount(**pars) == legacy.getRecordCount(**pars)


# ---------------------------------------------------------------------------
#  The switch
# ---------------------------------------------------------------------------

def _app_handler_for(db, tmp_path, value):
    """Build page.app with ``db?app_handler`` set to *value* (None = absent)."""
    confnode = db.application.config.getNode('db')
    previous = confnode.attr.pop('app_handler', None)
    if value is not None:
        confnode.attr['app_handler'] = value
    try:
        page = _StandInPage(db, str(tmp_path / ('switch_%s' % value)))
        return GnrWebPage.app.fget(page)
    finally:
        confnode.attr.pop('app_handler', None)
        if previous is not None:
            confnode.attr['app_handler'] = previous


def test_switch_absent_gives_the_current_handler(db, tmp_path):
    handler = _app_handler_for(db, tmp_path, None)
    assert isinstance(handler, GnrWebAppHandler)
    assert not isinstance(handler, GnrWebAppHandlerNext)


def test_switch_next_gives_the_new_handler(db, tmp_path):
    handler = _app_handler_for(db, tmp_path, 'next')
    assert isinstance(handler, GnrWebAppHandlerNext)


def test_switch_other_value_gives_the_current_handler(db, tmp_path):
    handler = _app_handler_for(db, tmp_path, 'whatever')
    assert isinstance(handler, GnrWebAppHandler)
    assert not isinstance(handler, GnrWebAppHandlerNext)


# ---------------------------------------------------------------------------
#  The table proxy
# ---------------------------------------------------------------------------

def test_saved_query_loaded_by_the_proxy(pg_handlers, db_postgres):
    """The proxy loaders return what the inherited flow loads inline."""
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = 7
    query_id = _new_userobject(db_postgres, 'test_proxy_query', 'query', data)
    loaded = db_postgres.table('invc.customer').selectionProxy().loadSavedQuery(query_id)
    assert loaded['queryLimit'] == 7
    assert loaded['where'].toXml() == data['where'].toXml()


def test_saved_view_loaded_by_the_proxy(pg_handlers, db_postgres):
    viewbag = _customer_view_bag()
    view_id = _new_userobject(db_postgres, 'test_proxy_view', 'view', viewbag)
    loaded = db_postgres.table('invc.customer').selectionProxy().loadSavedView(view_id)
    assert loaded.toXml() == viewbag.toXml()


def test_selection_proxy_is_cached(db):
    tblobj = db.table('invc.customer')
    assert tblobj.selectionProxy() is tblobj.selectionProxy()


def test_selection_proxy_knows_its_table(db):
    tblobj = db.table('invc.customer')
    assert tblobj.selectionProxy().tblobj is tblobj
