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
    """Only the page ids added to ``live_pages`` are registered."""

    def __init__(self):
        self.live_pages = set()

    def exists(self, page_id, register_name=None):
        return page_id in self.live_pages


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
        handlers = []
        for name, handler_class in (('legacy', GnrWebAppHandler),
                                    ('next', GnrWebAppHandlerNext)):
            page = _StandInPage(db, str(tmp_path / name))
            handler = handler_class(page)
            # _prepareRpcQuery reaches the handler back through page.app
            page.app = handler
            handlers.append(handler)
        return tuple(handlers)
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


def _assert_same(handlers, _ignore=(), **pars):
    """Run the same call through both handlers and compare rows and attributes.

    *_ignore* names the result attributes a documented divergence covers, so
    the rest of the case still proves equivalence.
    """
    legacy_result, next_result = _run_both(handlers, **pars)
    legacy_rows, legacy_attrs = _normalized(legacy_result)
    next_rows, next_attrs = _normalized(next_result)
    if _ignore:
        legacy_attrs = {k: v for k, v in legacy_attrs.items() if k not in _ignore}
        next_attrs = {k: v for k, v in next_attrs.items() if k not in _ignore}
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
    # whereAsPlainText is the declared divergence of #1359, asserted by
    # test_saved_query_where_as_plain_text_only_in_next
    rows, _ = _assert_same(pg_handlers, _ignore=('whereAsPlainText',),
                           table='invc.customer',
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
    rows, _ = _assert_same(pg_handlers, _ignore=('whereAsPlainText',),
                           table='invc.customer', savedQuery=query_id,
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


# ---------------------------------------------------------------------------
#  Shared helpers of the phase 2 cases
# ---------------------------------------------------------------------------

def _first_pkeys(db, howmany):
    """The first *howmany* pkeys of invc.customer, ordered by pkey."""
    return [r['id'] for r in db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=howmany).fetch()]


def _assert_same_failure(handlers, exception=Exception, **pars):
    """Both handlers must fail the same way on the same call."""
    failures = []
    for handler in handlers:
        with pytest.raises(exception) as err:
            handler.getSelection(**pars)
        failures.append((type(err.value).__name__, str(err.value)))
    assert failures[1] == failures[0]
    return failures[0]


def _custom_order_by_bag(fieldpath, sorting):
    entry = Bag()
    entry['fieldpath'] = fieldpath
    entry['sorting'] = sorting
    bag = Bag()
    bag['r_0'] = entry
    return bag


# ---------------------------------------------------------------------------
#  A. prologue
# ---------------------------------------------------------------------------

def test_multistores_becomes_the_store_name(handlers):
    """A2 - multiStores travels to the query as ``_storename``."""
    name, message = _assert_same_failure(handlers, table='invc.customer',
                                         columns='$account_name',
                                         multiStores='not_a_store')
    assert 'not_a_store' in message


def test_query_extra_pars_become_query_kwargs(handlers):
    """A3 - queryExtraPars is merged into the query kwargs."""
    extra = Bag()
    extra['wanted_state'] = 'VIC'
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,$state',
                           condition='$state = :wanted_state', queryExtraPars=extra,
                           order_by='$account_name')
    assert rows
    assert {row[1]['state'] for row in rows} == {'VIC'}


def test_hard_query_limit_applies_when_limit_is_none(handlers):
    """A4 - hardQueryLimit becomes the limit and is reported as reached."""
    rows, attrs = _assert_same(handlers, table='invc.customer',
                               columns='$account_name',
                               order_by='$account_name', hardQueryLimit=3)
    assert len(rows) == 3
    assert attrs['hardQueryLimitOver'] is True


def test_formula_variants_reach_the_query(handlers):
    """A6 - formulaVariants becomes one dict kwarg per cell."""
    variant = Bag()
    variant['x'] = 1
    variants = Bag()
    variants['subtable_residential'] = variant
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           order_by='$account_name', limit=2, formulaVariants=variants)
    assert len(rows) == 2


def test_save_rpc_query_returns_the_serialized_query(handlers):
    """A7 - saveRpcQuery returns the serialized query and no data."""
    legacy_result, next_result = _run_both(handlers, table='invc.customer',
                                           columns='$account_name',
                                           where=_customer_where_bag(),
                                           saveRpcQuery=True)
    assert next_result[1]['rpcquery'] == legacy_result[1]['rpcquery']
    assert 'sqlquery' in next_result[1]['rpcquery']
    assert len(list(next_result[0])) == 0


def test_check_permissions_true_uses_the_page_pars(handlers):
    """A8 - the literal True is replaced by page.permissionPars."""
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           order_by='$account_name', limit=2, checkPermissions=True)
    assert len(rows) == 2


def test_format_kwarg_is_applied_only_by_next(handlers):
    """A9 - DIVERGENCE: legacy stores the format under a slice object.

    ``formats[7:] = kwargs.pop(k)`` writes under the key ``slice(7, None)``
    instead of under the column name, so the requested format is never
    applied; the dict is non empty though, so every value is still converted
    to text.  Next writes under ``k[7:]`` and the column is formatted.
    """
    legacy, nxt = handlers
    pars = dict(table='invc.invoice', columns='$inv_number,$total',
                order_by='$inv_number', limit=1, format_total='#,###.00')
    legacy_rows, _ = _normalized(legacy.getSelection(**pars))
    next_rows, _ = _normalized(nxt.getSelection(**pars))
    assert ',' not in legacy_rows[0][1]['total']
    assert ',' in next_rows[0][1]['total']
    assert next_rows[0][1]['total'].replace(',', '') == legacy_rows[0][1]['total']


# ---------------------------------------------------------------------------
#  B. selectionName and frozen selections
# ---------------------------------------------------------------------------

def test_selection_name_star_uses_the_page_id(handlers):
    """B1 - '*' is replaced by the page id."""
    _, attrs = _assert_same(handlers, table='invc.customer', columns='$account_name',
                            order_by='$account_name', limit=2, selectionName='*')
    assert attrs['selectionName'] == 'test_page'


def test_selection_name_star_prefix_is_stripped(handlers):
    """B1 - '*name' is replaced by 'name' and never unfrozen."""
    _, attrs = _assert_same(handlers, table='invc.customer', columns='$account_name',
                            order_by='$account_name', limit=2, selectionName='*b1')
    assert attrs['selectionName'] == 'b1'


def test_named_selection_comes_from_the_pickle(handlers):
    """B2 - a named selection already frozen skips the whole query phase."""
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=3, selectionName='*b2')
    rows, attrs = _assert_same(handlers, table='invc.customer', selectionName='b2')
    assert attrs['debug'] == 'fromPickle'
    assert 'totalrows' not in attrs
    assert len(rows) == 3


def test_named_selection_is_resorted(handlers):
    """B2 - a different sortedBy re-sorts and re-freezes the pickle."""
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=4, selectionName='*b2s')
    rows, attrs = _assert_same(handlers, table='invc.customer', selectionName='b2s',
                               sortedBy='account_name')
    assert attrs['debug'] == 'fromPickle'
    assert len(rows) == 4


# ---------------------------------------------------------------------------
#  C. new selection
# ---------------------------------------------------------------------------

def test_from_selection_takes_its_pkeys(handlers):
    """C5 - fromSelection replaces pkeys with the frozen pkey list."""
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=3, selectionName='*c5')
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           fromSelection='c5')
    assert len(rows) == 3


def test_custom_order_by(handlers):
    """C6 - a customOrderBy bag becomes the order_by string."""
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           customOrderBy=_custom_order_by_bag('account_name', False),
                           limit=3)
    names = [row[1]['account_name'] for row in rows]
    assert names == sorted(names, reverse=True)


def test_selectmethod_returning_false(handlers):
    """C10 - a selectmethod returning False returns table and selectionName."""
    for handler in handlers:
        handler.page.rpc_methods['false_method'] = lambda **kwargs: False
    legacy_result, next_result = _run_both(handlers, table='invc.customer',
                                           selectmethod='false_method')
    assert next_result[1] == legacy_result[1]
    assert next_result[1] == dict(table='invc.customer', selectionName='')
    assert len(list(next_result[0])) == 0


def test_selectmethod_returning_a_list_raises(handlers):
    """C11 - a selectmethod returning a list calls _default_getSelection()
    with no arguments, so both handlers die on a None table object."""
    for handler in handlers:
        handler.page.rpc_methods['list_method'] = lambda **kwargs: ['a', 'b']
    raised = []
    for handler in handlers:
        with pytest.raises(AttributeError) as err:
            handler.getSelection(table='invc.customer', selectmethod='list_method')
        raised.append(type(err.value))
    assert raised[1] is raised[0]


def test_weak_logical_deleted_retries_the_query(handlers):
    """C12 - an empty selection is queried again with excludeLogicalDeleted='mark'."""
    calls = {}

    def make_counting(handler, name):
        def counting(**pars):
            calls.setdefault(name, []).append(pars['excludeLogicalDeleted'])
            return handler._default_getSelection(**pars)
        return counting

    for name, handler in zip(('legacy', 'next'), handlers):
        handler.page.rpc_methods['counting_method'] = make_counting(handler, name)
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           condition="$account_name = 'no such customer'",
                           weakLogicalDeleted=True, selectmethod='counting_method')
    assert rows == []
    assert calls['legacy'] == [True, 'mark']
    assert calls['next'] == calls['legacy']


def test_external_store_column_fails_the_same_way(handlers):
    """C13 - a ':' column asks for an external store the rows do not carry."""
    failures = []
    for handler in handlers:
        with pytest.raises(KeyError) as err:
            handler.getSelection(table='invc.customer',
                                 columns='$account_name,invc.customer.state:name',
                                 limit=2)
        failures.append(str(err.value))
    assert failures[1] == failures[0] == "'_external_store'"


def test_apply_method_merges_its_result(handlers):
    """C14 - the applymethod receives the apply_* kwargs and its result is merged."""
    received = {}

    def make_apply(name):
        def apply_method(selection, **pars):
            received[name] = pars
            return dict(applied=len(selection))
        return apply_method

    for name, handler in zip(('legacy', 'next'), handlers):
        handler.page.rpc_methods['apply_method'] = make_apply(name)
    _, attrs = _assert_same(handlers, table='invc.customer', columns='$account_name',
                            order_by='$account_name', limit=2,
                            applymethod='apply_method', apply_extra='x')
    assert attrs['applied'] == 2
    assert received['next'] == received['legacy'] == dict(extra='x')


def test_named_selection_is_frozen_and_recorded(handlers):
    """C15 - the selection is frozen and its path stored in the user store."""
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=2, selectionName='*c15')
    for handler in handlers:
        path = handler.page.userStore().getItem(
            'current.table.invc_customer.last_selection_path')
        assert path
        assert handler.page.unfreezeSelection(
            handler.db.table('invc.customer'), 'c15') is not None


def test_pkeys_with_only_commas_selects_nothing(handlers):
    """D4 of the design - the ``kwargs['limit'] = 0`` branch is unreachable.

    A falsy pkeys never enters the branch and a truthy one always yields at
    least one element after ``strip(',').split(',')``, so the duplicate
    ``limit`` keyword can never be produced.
    """
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           pkeys=',')
    assert rows == []


# ---------------------------------------------------------------------------
#  D. the default query executor
# ---------------------------------------------------------------------------

def test_sql_context_without_conditions(handlers):
    """D1/D12 - an empty SQL context leaves the query untouched."""
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           order_by='$account_name', limit=2, sqlContextName='ctx_empty')
    assert len(rows) == 2


def test_sql_context_join_condition(handlers):
    """D12 - the join conditions of a SQL context are applied by the handler,
    including the ``<context>_<value>`` hook resolved on the handler itself."""
    joinbag = Bag(dict(target_fld='invc.customer.state', from_fld='invc.state.code',
                       condition='$name = :sname', one_one=False, applymethod=None,
                       params=Bag(dict(sname='dynamic'))))
    for handler in handlers:
        handler.page.pageStore().setItem(
            '_sqlctx.conditions.ctx.invc_customer_state_invc_state_code', joinbag)
        handler.ctx_dynamic = lambda: 'New South Wales'
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,@state.name',
                           order_by='$account_name', sqlContextName='ctx', limit=5)
    assert rows


def test_linked_selection(handlers, db):
    """D2 - a linked selection replaces the where with the master pkeys."""
    pkeys = _first_pkeys(db, 2)
    pars = Bag(dict(pkeys=','.join(pkeys), command=None, gridNodeId='grid_1',
                    linkedPageId=None, linkedSelectionName='master_sel',
                    masterTable='invc.customer', relationpath='$id'))
    for handler in handlers:
        handler.page.pageStore().setItem('linkedSelectionPars.d2', pars)
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           selectionName='d2')
    assert len(rows) == 2


def test_filtering_pkeys_rpc_returns_a_selection(handlers, db):
    """D8 - a filtering rpc may return a selection, read as a pkey list."""
    def filter_method(**kwargs):
        return db.table('invc.customer').query(columns='$id', order_by='$id',
                                               limit=3).selection()
    for handler in handlers:
        handler.page.rpc_methods['sel_filter'] = filter_method
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           filteringPkeys='sel_filter')
    assert len(rows) == 3


def test_filtering_pkeys_rpc_forces_the_order_by(handlers, db):
    """D8 - forcedOrderBy on the returned selection overrides the order_by."""
    def filter_method(**kwargs):
        selection = db.table('invc.customer').query(columns='$id', order_by='$id',
                                                    limit=4).selection()
        selection.forcedOrderBy = '$account_name'
        return selection
    for handler in handlers:
        handler.page.rpc_methods['forced_filter'] = filter_method
    rows, _ = _assert_same(handlers, table='invc.customer', columns='$account_name',
                           filteringPkeys='forced_filter', order_by='$state')
    names = [row[1]['account_name'] for row in rows]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
#  E. output and result attributes
# ---------------------------------------------------------------------------

def test_add_classes_from_col_attrs(handlers):
    """E2 - a column carrying _addClass adds a custom class to its rows."""
    rows, _ = _assert_same(handlers, table='invc.customer',
                           columns='$account_name,$subtable_residential',
                           order_by='$account_name', limit=10)
    assert any('subtable_residential' in (row[1].get('_customClasses') or '')
               for row in rows)


def test_newproc_is_always_no(handlers):
    """E5 - the attribute name is the literal 'self.newprocess', never set."""
    for handler in handlers:
        _, attrs = handler.getSelection(table='invc.customer',
                                        columns='$account_name', limit=1)
        assert attrs['newproc'] == 'no'


def test_total_row_count_counts_the_condition_only(handlers):
    """E6 - totalRowCount ignores the where bag and counts on the condition."""
    rows, attrs = _assert_same(handlers, table='invc.customer',
                               columns='$account_name,$state',
                               where=_customer_where_bag(),
                               condition='$state IS NOT NULL', totalRowCount=True)
    assert attrs['totalRowCount'] > len(rows)


def test_prev_selected_idx(handlers, db):
    """E8 - prevSelectedDict is translated into the row indexes."""
    pkeys = _first_pkeys(db, 2)
    _, attrs = _assert_same(handlers, table='invc.customer', columns='$account_name',
                            order_by='$id', selectionName='*e8',
                            prevSelectedDict={pkeys[0]: True})
    assert attrs['prevSelectedIdx'] == [0]


def test_hard_query_limit_over_on_a_frozen_selection_diverges(handlers):
    """E10 - DIVERGENCE: the fromPickle path has no 'totalrows' attribute.

    Legacy reads ``resultAttributes['totalrows']``, which the frozen path
    never sets, and raises KeyError as soon as hardQueryLimit is truthy.
    Next computes the comparison from the length of the selection.
    """
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=3, selectionName='*e10')
    legacy, nxt = handlers
    with pytest.raises(KeyError):
        legacy.getSelection(table='invc.customer', selectionName='e10',
                            hardQueryLimit=3)
    _, attrs = nxt.getSelection(table='invc.customer', selectionName='e10',
                                hardQueryLimit=3)
    assert attrs['hardQueryLimitOver'] is True


def test_slave_selection_of_a_dead_page_is_dropped(handlers):
    """E11 - a slave registered on a page that no longer exists is removed."""
    for handler in handlers:
        grids = Bag()
        grids['grid_1'] = True
        handler.page.pageStore().setItem('slaveSelections.e11.dead_page', grids)
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=2, selectionName='*e11')
    for handler in handlers:
        assert handler.page.pageStore().getItem('slaveSelections.e11.dead_page') is None
        assert handler.page.published == []


def test_slave_selection_of_a_live_page_is_notified(handlers):
    """E11 - every grid of a live slave page gets a refresh publish."""
    for handler in handlers:
        grids = Bag()
        grids['grid_2'] = True
        handler.page.pageStore().setItem('slaveSelections.e11b.live_page', grids)
        handler.page.site.register.live_pages.add('live_page')
    _assert_same(handlers, table='invc.customer', columns='$account_name',
                 order_by='$account_name', limit=2, selectionName='*e11b')
    for handler in handlers:
        assert handler.page.published == [
            ('grid_2_refreshLinkedSelection', dict(value=True, page_id='live_page'))]


# ---------------------------------------------------------------------------
#  F. columns
# ---------------------------------------------------------------------------

def test_bracket_group_columns_diverge(handlers):
    """F4 - DIVERGENCE: legacy never closes a bracket group.

    ``col`` has already lost its ']' when the closing test runs, so
    ``maintable`` is never reset and every following column keeps the prefix
    of the group.  Next remembers the group end before stripping it.
    """
    legacy, nxt = handlers
    tblobj = legacy.db.table('invc.customer')
    spec = '@state[name,code],$account_name'
    legacy_columns, _ = legacy._getSelection_columns(tblobj, spec)
    next_columns, _ = nxt._getSelection_columns(tblobj, spec)
    assert legacy_columns == '@state.name,@state.code,@state.$account_name'
    assert next_columns == '@state.name,@state.code,$account_name'


def test_bracket_group_columns_query(handlers):
    """F4 - the fixed column list is a query the database accepts."""
    legacy, nxt = handlers
    rows, attrs = _normalized(nxt.getSelection(table='invc.customer',
                                               columns='@state[name],$account_name',
                                               order_by='$account_name', limit=2))
    assert len(rows) == 2
    assert 'account_name' in rows[0][1]
    with pytest.raises(Exception):
        legacy.getSelection(table='invc.customer',
                            columns='@state[name],$account_name',
                            order_by='$account_name', limit=2)


# ---------------------------------------------------------------------------
#  getRecordCount and the rpc query, both folded onto the proxy
# ---------------------------------------------------------------------------

def test_get_record_count_by_field(handlers):
    legacy, nxt = handlers
    pars = dict(field='invc.customer.state', value='NSW')
    counted = legacy.getRecordCount(**pars)
    assert counted > 0
    assert nxt.getRecordCount(**pars) == counted


def test_get_record_count_with_condition(handlers):
    legacy, nxt = handlers
    pars = dict(table='invc.customer', condition="$state = 'VIC'")
    counted = legacy.getRecordCount(**pars)
    assert counted > 0
    assert nxt.getRecordCount(**pars) == counted


def test_get_record_count_where_bag_and_condition(handlers):
    legacy, nxt = handlers
    pars = dict(table='invc.customer', where=_customer_where_bag(),
                condition='$account_name IS NOT NULL')
    counted = legacy.getRecordCount(**pars)
    assert counted > 0
    assert nxt.getRecordCount(**pars) == counted


def test_record_count_on_the_proxy(handlers, db):
    legacy, _ = handlers
    tblobj = db.table('invc.customer')
    assert tblobj.selectionProxy().recordCount(
        where=_customer_where_bag(), customOpCbDict={}) == legacy.getRecordCount(
            table='invc.customer', where=_customer_where_bag())


def test_rpc_query_on_the_proxy(handlers, db):
    legacy, _ = handlers
    tblobj = db.table('invc.customer')
    proxy_query = tblobj.selectionProxy().rpcQuery(
        columns='$account_name', where=_customer_where_bag(), customOpCbDict={})
    legacy_query = legacy._prepareRpcQuery(tblobj=tblobj, columns='$account_name',
                                           where=_customer_where_bag())
    assert proxy_query.toXml() == legacy_query.toXml()


# ---------------------------------------------------------------------------
#  Saved queries: the three divergences of #1359 (postgres only)
# ---------------------------------------------------------------------------

def test_saved_query_where_as_plain_text_only_in_next(pg_handlers, db_postgres):
    """#1359 - DIVERGENCE: legacy derives ``wherebag`` from the caller's where
    before the saved query is loaded, so a saved query never gets the
    whereAsPlainText attribute.  Next derives it after the saved query."""
    data = Bag()
    data['where'] = _customer_where_bag()
    data['queryLimit'] = 5
    query_id = _new_userobject(db_postgres, 'test_wapt_query', 'query', data)
    legacy, nxt = pg_handlers
    pars = dict(table='invc.customer', columns='$account_name,$state',
                savedQuery=query_id, order_by='$account_name')
    legacy_rows, legacy_attrs = _normalized(legacy.getSelection(**pars))
    next_rows, next_attrs = _normalized(nxt.getSelection(**pars))
    assert next_rows == legacy_rows
    assert 'whereAsPlainText' not in legacy_attrs
    assert next_attrs['whereAsPlainText']


def test_saved_query_empty_limit_falls_back_only_in_next(pg_handlers, db_postgres):
    """#1359 - DIVERGENCE: a saved query with no queryLimit overwrites the
    hardQueryLimit fallback in legacy, so the hard limit is bypassed.  Next
    applies the fallback again after the saved query."""
    data = Bag()
    data['where'] = _customer_where_bag()
    query_id = _new_userobject(db_postgres, 'test_nolimit_query', 'query', data)
    legacy, nxt = pg_handlers
    pars = dict(table='invc.customer', columns='$account_name,$state',
                savedQuery=query_id, order_by='$account_name', hardQueryLimit=2)
    legacy_rows, _ = _normalized(legacy.getSelection(**pars))
    next_rows, _ = _normalized(nxt.getSelection(**pars))
    assert len(legacy_rows) > 2
    assert len(next_rows) == 2


def test_saved_query_without_where(pg_handlers, db_postgres):
    """C1 - a saved query whose ``where`` is empty means no filter.

    Legacy leaves the whole userobject record in the ``where`` variable and
    hands it to the where bag decoder; ``sqlWhereFromBag`` finds no condition
    node in it and returns an empty WHERE, so the defect stays latent for
    every record shape adm.userobject produces.  Next reads the saved where
    whatever it contains, which gives the same rows by the intended route.
    """
    data = Bag()
    data['queryLimit'] = 3
    query_id = _new_userobject(db_postgres, 'test_nowhere_query', 'query', data)
    rows, _ = _assert_same(pg_handlers, table='invc.customer',
                           columns='$account_name', savedQuery=query_id,
                           order_by='$account_name', limit=5)
    assert len(rows) == 5
