"""Equivalence between the dbSelect flows of the two handlers.

``GnrWebAppHandlerNext`` moves the table level part of ``dbSelect``,
``dbSelect_default``, ``tableAnalyzeStore``, ``getValuesString`` and
``getMultiFetch`` onto an app level table proxy (``tblobj.dbSelectProxy()``).
It is a refactoring, so every input must give the same result Bag and the same
result attributes through both handlers; the two declared divergences are the
defect fixes of ``bugs_dbselect.md`` and each of them has a test that asserts
the divergence instead of the equality.

Every case below covers one row of the behaviour tables in
``.subtasks/alt-apphandler/progress_dbselect.md``, step P4.1, named in its
docstring.

The database and the fixtures come from ``apphandler_next_common``, shared with
the other flow suites.  Its stand-in page does not carry the four services this
flow needs — ``page._``, ``page.getUuid``, ``page.lazyBag`` and the
``site.getStaticPath`` the last one calls — and that module belongs to another
flow, so they are added here by subclassing.
"""

import os

import pytest

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.apphandler_next import GnrWebAppHandlerNext

from apphandler_next_common import _StandInPage, _StandInSite
# pytest resolves fixtures by name in the module namespace, so the shared ones
# are imported even though nothing in this file calls them.
from apphandler_next_common import (gnr_test_config, db,  # noqa: F401
                                    db_with_external_store)


# ---------------------------------------------------------------------------
#  The stand-in page of this flow
# ---------------------------------------------------------------------------

class _StaticSite(_StandInSite):
    """The shared stand-in site plus ``getStaticPath``.

    ``tableAnalyzeStore`` writes the totalized Bag through ``page.lazyBag``,
    which asks the site for the directory of the ``page:explorer`` static
    location.  The real implementation splits the location on ``:``, resolves
    it through a static handler and creates the directory when *autocreate* is
    given; here the location becomes one folder under a temporary root, with
    the same *autocreate* convention (``True`` all the arguments, a negative
    number all but the last ones).
    """

    def __init__(self, gnrapp, static_root):
        super().__init__(gnrapp)
        self.static_root = static_root

    def getStaticPath(self, static, *args, **kwargs):
        autocreate = kwargs.pop('autocreate', False)
        base = os.path.join(self.static_root, static.replace(':', '_'))
        args = [a for a in args if a]
        if autocreate:
            created = args if autocreate is True else args[:autocreate]
            os.makedirs(os.path.join(base, *created), exist_ok=True)
        return os.path.join(base, *args)


class _DbSelectPage(_StandInPage):
    """The shared stand-in page plus the three services the dbSelect flow uses.

    ``_`` records what it was asked to translate, so a case can assert that the
    column headers went through the localizer; ``getUuid`` is fixed, so the
    explorer pickle of ``tableAnalyzeStore`` lands on a predictable path;
    ``lazyBag`` is the real ``GnrWebPage`` implementation, unbound, as the
    freeze methods of the shared stand-in already are.
    """

    def __init__(self, db, connectionFolder, page_id='test_page'):
        super().__init__(db, connectionFolder, page_id=page_id)
        self.site = _StaticSite(db.application, connectionFolder)
        self.translated = []

    def _(self, text, **kwargs):
        self.translated.append(text)
        return text

    def getUuid(self):
        return 'explorer-fixed-uuid'

    def lazyBag(self, bag, name=None, location='page:resolvers'):
        return GnrWebPage.lazyBag(self, bag, name=name, location=location)


@pytest.fixture
def make_dbselect_proxys(tmp_path):
    """Build one handler of each class on a given database."""
    def build(database):
        built = []
        for name, handler_class in (('legacy', GnrWebAppHandler),
                                    ('next', GnrWebAppHandlerNext)):
            folder = str(tmp_path / name)
            os.makedirs(folder, exist_ok=True)
            page = _DbSelectPage(database, folder)
            handler = handler_class(page)
            page.app = handler
            built.append(handler)
        return tuple(built)
    return build


@pytest.fixture
def handlers(make_dbselect_proxys, db):
    return make_dbselect_proxys(db)


@pytest.fixture
def store_handlers(make_dbselect_proxys, db_with_external_store):
    return make_dbselect_proxys(db_with_external_store)


@pytest.fixture
def table_attribute(db):
    """Set a table attribute for the duration of one test."""
    restore = []

    def setter(table, name, value):
        attributes = db.table(table).attributes
        restore.append((attributes, name, name in attributes, attributes.get(name)))
        attributes[name] = value
    yield setter
    for attributes, name, existed, old in reversed(restore):
        if existed:
            attributes[name] = old
        else:
            attributes.pop(name, None)


@pytest.fixture
def optranslate_spy(db):
    """Record the operator and the incoming ``sqlArgs`` of every opTranslate.

    The real method runs: the spy is an instance attribute that shadows the
    class one and forwards to it, so the conditions and the rows are the real
    ones.  What it captures is the state of the ``sqlArgs`` dict the caller
    handed over, which is what the two search stages disagree about.
    """
    installed = []

    def install(table):
        tblobj = db.table(table)
        calls = []
        original = tblobj.__class__.opTranslate

        def spy(column, op, value, dtype=None, sqlArgs=None):
            calls.append((op, dict(sqlArgs or {})))
            return original(tblobj, column, op, value, dtype=dtype,
                            sqlArgs=sqlArgs)
        tblobj.opTranslate = spy
        installed.append(tblobj)
        return calls
    yield install
    for tblobj in installed:
        del tblobj.opTranslate


# ---------------------------------------------------------------------------
#  Comparison helpers
# ---------------------------------------------------------------------------

VOLATILE = ('dbselect_time',)


def _rows(bag):
    return [(node.label, dict(node.attr)) for node in bag]


def _normalized(result):
    rows, attributes = result
    return _rows(rows), {k: v for k, v in attributes.items() if k not in VOLATILE}


def _assert_same_dbselect(handlers, **pars):
    """Run the same dbSelect through both handlers and compare the outcome."""
    legacy, nxt = handlers
    legacy_result = _normalized(legacy.dbSelect(**pars))
    next_result = _normalized(nxt.dbSelect(**pars))
    assert next_result == legacy_result
    return legacy_result


def _assert_same_call(handlers, method, **pars):
    """Run the same call through both handlers and compare the return value."""
    legacy, nxt = handlers
    legacy_result = getattr(legacy, method)(**pars)
    next_result = getattr(nxt, method)(**pars)
    assert next_result == legacy_result
    return legacy_result


# ---------------------------------------------------------------------------
#  Data helpers
# ---------------------------------------------------------------------------

def _first_customer(db):
    return db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=1).fetch()[0]['id']


CUSTOMER = 'invc.customer'


# ---------------------------------------------------------------------------
#  A. prologue
# ---------------------------------------------------------------------------

def test_plain_search(handlers):
    """A7-A11, D5-D7, D9 - the plain search: same rows, same attributes."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=3)
    assert [label for label, _ in rows][-1] == 'null_row'
    assert attributes['columns'] == 'account_name'
    assert attributes['resultClass'] == ''


def test_querystring_and_underscore_querystring(handlers):
    """A5 - two parameters for one value, and _querystring wins."""
    underscore = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=3)
    plain = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, querystring='Archer', limit=3)
    both = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer',
        querystring='Isla', limit=3)
    assert plain == underscore
    assert both == underscore


def test_limit_defaults_to_the_app_config(handlers):
    """A6 - with no limit the app config default (10) applies."""
    legacy = handlers[0]
    assert legacy.gnrapp.config.get('dbselect?limit', 10) == 10
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer')
    assert len([label for label, _ in rows if label != 'null_row']) == 10


def test_limit_is_coerced_to_int(handlers):
    """A6 - a limit sent as a string by the client is coerced."""
    as_string = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                      _querystring='Archer', limit='3')
    as_int = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                   _querystring='Archer', limit=3)
    assert as_string == as_int


def test_rowcaption_changes_the_caption_and_the_columns(handlers):
    """A8 - a custom rowcaption drives both the caption and the columns."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=2,
        rowcaption='$account_name,$email:%s <%s>')
    assert attributes['columns'] == 'account_name,email'
    assert ' <' in rows[0][1]['caption']


def test_columns_parameter_drives_the_search(handlers):
    """A9 - the columns parameter replaces the caption columns in the search."""
    rows, _ = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='gmail.com', limit=3,
        columns='$email')
    assert [label for label, _ in rows if label != 'null_row']


def test_aux_columns_are_shown(handlers):
    """A10, D4 - auxColumns join the shown columns and the headers."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=2,
        auxColumns='$email,$phone')
    assert attributes['columns'] == 'account_name,email,phone'
    assert 'email' in rows[0][1]


def test_hidden_columns_are_fetched_not_shown(handlers):
    """A11 - hiddenColumns reach the rows and stay out of the headers."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=2,
        hiddenColumns='$email')
    assert attributes['columns'] == 'account_name'
    assert 'email' in rows[0][1]


def test_alternate_pkey_is_added_to_the_columns(handlers):
    """A12 - alternatePkey joins the result columns with a $ prefix."""
    rows, _ = _assert_same_dbselect(
        handlers, dbtable='invc.customer', _querystring='Archer', limit=2,
        alternatePkey='email')
    assert 'email' in rows[0][1]


def test_alternate_pkey_already_prefixed(handlers):
    """A12 - an alternatePkey that already starts with $ is not prefixed twice."""
    prefixed = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=2,
        alternatePkey='$email')
    plain = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=2,
        alternatePkey='email')
    assert prefixed == plain


def test_storename_switch_is_not_reverted(store_handlers, db_with_external_store):
    """A1 - the store switch stays on the thread env after the call (DS1)."""
    database = db_with_external_store
    for handler in store_handlers:
        try:
            handler.dbSelect(dbtable=CUSTOMER, _querystring='Archer',
                             _storename='extstore', limit=2)
            assert database.currentEnv.get('storename') == 'extstore'
            handler.dbSelect(dbtable=CUSTOMER, _querystring='Archer',
                             _storename=False, limit=2)
            assert database.currentEnv.get('storename') is None
        finally:
            database.use_store()


def test_storename_none_leaves_the_store_alone(store_handlers,
                                               db_with_external_store):
    """A1 - _storename None touches nothing, not even to reset."""
    database = db_with_external_store
    try:
        database.use_store('extstore')
        for handler in store_handlers:
            handler.dbSelect(dbtable=CUSTOMER, _querystring='Archer', limit=2)
            assert database.currentEnv.get('storename') == 'extstore'
    finally:
        database.use_store()


# ---------------------------------------------------------------------------
#  B. the _id branch
# ---------------------------------------------------------------------------

def test_by_id(handlers, db):
    """B2, B5, D9 - one row by pkey, and no null row."""
    pkey = _first_customer(db)
    rows, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                             _id=pkey)
    assert [label for label, _ in rows] == [pkey]
    assert 'errors' not in attributes


def test_by_id_on_the_alternate_pkey(handlers, db):
    """B2 - with alternatePkey the _id is matched on that column."""
    email = db.table(CUSTOMER).query(
        columns='$email', where='$email IS NOT NULL',
        order_by='$email', limit=1).fetch()[0]['email']
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER, _id=email,
                                    alternatePkey='email')
    assert len(rows) == 1


def test_by_id_with_a_condition(handlers, db):
    """B3 - a matching condition is AND-ed and no error is reported."""
    pkey = _first_customer(db)
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _id=pkey,
        condition='$account_name IS NOT NULL')
    assert [label for label, _ in rows] == [pkey]
    assert 'errors' not in attributes


def test_by_id_condition_not_matched_reports_an_error(handlers, db):
    """B6 - the row wins over the condition, and errors says so."""
    pkey = _first_customer(db)
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _id=pkey,
        condition="$account_name = 'no such name'")
    assert [label for label, _ in rows] == [pkey]
    assert attributes['errors'] == 'current value does not fit condition'


def test_by_id_weak_condition_skips_the_condition(handlers, db):
    """B3 - weakCondition True makes the _id fetch ignore the condition."""
    pkey = _first_customer(db)
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _id=pkey,
        condition="$account_name = 'no such name'", weakCondition=True)
    assert [label for label, _ in rows] == [pkey]
    assert 'errors' not in attributes


def test_by_id_unknown_key_gives_an_empty_result(handlers):
    """B5, D3 - an _id nobody has gives the bare Bag."""
    rows, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                             _id='no-such-pkey')
    assert rows == []
    assert 'columns' not in attributes


# ---------------------------------------------------------------------------
#  C. the querystring branch
# ---------------------------------------------------------------------------

def test_stars_are_stripped(handlers):
    """C1 - leading and trailing stars are removed from the query."""
    starred = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='*Archer*', limit=3)
    plain = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                  _querystring='Archer', limit=3)
    assert starred == plain


def test_numeric_query_is_prefixed_with_percent(handlers, db):
    """C2 - a wholly numeric query becomes a suffix match."""
    invoice = db.table('invc.invoice').query(
        columns='$inv_number', where='$inv_number IS NOT NULL',
        order_by='$inv_number', limit=1).fetch()[0]['inv_number']
    tail = invoice[-3:]
    rows, _ = _assert_same_dbselect(handlers, dbtable='invc.invoice',
                                    _querystring=tail, limit=5)
    assert tail.isdigit()
    assert [label for label, _ in rows if label != 'null_row']


def test_selectmethod_receives_the_search_parameters(handlers, db):
    """A13, C3, C11, E11 - the select handler contract, eleven keywords."""
    tblobj = db.table(CUSTOMER)
    seen = []

    def selectmethod(**kwargs):
        seen.append(kwargs)
        return tblobj.query(columns='$account_name', limit=2).selection()
    for handler in handlers:
        handler.page.rpc_methods['mysel'] = selectmethod
    _assert_same_dbselect(handlers, dbtable=CUSTOMER, _querystring='Archer',
                          selectmethod='mysel', limit=4)
    assert sorted(seen[0]) == ['condition', 'exclude', 'excludeDraft',
                               'identifier', 'ignoreCase', 'limit', 'order_by',
                               'querycolumns', 'querystring', 'resultcolumns',
                               'tblobj']
    assert seen[0]['identifier'] == 'pkey'
    assert seen[0]['ignoreCase'] is True
    assert seen[0]['limit'] == 4
    assert seen[0]['order_by'] == '$account_name'
    assert seen[1] == seen[0]


def test_selectmethod_suppresses_the_weak_condition(handlers, db):
    """A3 - with a selectmethod the weak condition is switched off."""
    tblobj = db.table(CUSTOMER)
    seen = []

    def selectmethod(**kwargs):
        seen.append(kwargs)
        return tblobj.query(columns='$account_name', limit=2).selection()
    for handler in handlers:
        handler.page.rpc_methods['mysel'] = selectmethod
    _, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', selectmethod='mysel',
        condition="$state = 'ZZ'", weakCondition=True, limit=4)
    assert seen[0]['condition'] == "$state = 'ZZ'"
    assert attributes['resultClass'] == ''


def test_table_weak_condition_overrides_the_selectmethod_suppression(
        handlers, db, table_attribute):
    """C5 - the table attribute is read after the suppression and wins."""
    table_attribute(CUSTOMER, 'weakCondition', True)
    tblobj = db.table(CUSTOMER)

    def selectmethod(condition=None, **kwargs):
        if condition:
            return tblobj.query(columns='$account_name',
                                where=condition, limit=2).selection()
        return tblobj.query(columns='$account_name', limit=2).selection()
    for handler in handlers:
        handler.page.rpc_methods['mysel'] = selectmethod
    _, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', selectmethod='mysel',
        condition="$state = 'ZZ'", limit=4)
    assert attributes['resultClass'] == 'relaxedCondition'


def test_preferred_comes_from_the_table_attribute(handlers, table_attribute):
    """C4 - preferred None falls back to the table attribute."""
    table_attribute(CUSTOMER, 'preferred', "$state = 'NSW'")
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=3)
    assert '_customclasses_preferred' in rows[0][1]


def test_preferred_false_from_the_caller_wins(handlers, table_attribute):
    """C4 - an explicit falsy preferred is not replaced by the table one."""
    table_attribute(CUSTOMER, 'preferred', "$state = 'NSW'")
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=3,
                                    preferred=False)
    assert '_customclasses_preferred' not in rows[0][1]


def test_preferred_marks_and_sorts_the_rows(handlers):
    """C6, C9 - the preferred rows come first and carry the custom class."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=6,
                                    preferred="$state = 'NSW'")
    classes = [attr['_customclasses_preferred'] for label, attr in rows
               if label != 'null_row']
    assert classes == sorted(classes)


def test_invalid_item_condition_flags_the_rows(handlers):
    """C7 - invalidItemCondition adds the _is_invalid_item column."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=3,
                                    invalidItemCondition="$state = 'NSW'")
    assert '_is_invalid_item' in rows[0][1]


def test_order_by_falls_back_to_the_table_then_to_the_first_column(
        handlers, table_attribute):
    """C8 - explicit order_by, then the table attribute, then showcolumns[0]."""
    explicit = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                     _querystring='Archer', limit=4,
                                     order_by='$email')
    table_attribute(CUSTOMER, 'order_by', '$email')
    from_table = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                       _querystring='Archer', limit=4)
    assert from_table == explicit


def test_order_by_is_prefixed_with_a_dollar(handlers):
    """C8 - a bare column name is prefixed, an @ path is left alone."""
    bare = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                 _querystring='Archer', limit=4,
                                 order_by='email')
    dollar = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                   _querystring='Archer', limit=4,
                                   order_by='$email')
    assert bare == dollar


def test_weak_condition_true_relaxes_to_no_condition(handlers):
    """C12 - an empty result with weakCondition True retries without it."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=3,
        condition="$state = 'ZZ'", weakCondition=True)
    assert attributes['resultClass'] == 'relaxedCondition'
    assert [label for label, _ in rows if label != 'null_row']


def test_weak_condition_string_is_anded_then_dropped(handlers):
    """C10, C12 - a string weakCondition is an extra filter tried first."""
    rows, attributes = _assert_same_dbselect(
        handlers, dbtable=CUSTOMER, _querystring='Archer', limit=3,
        condition="$state = 'NSW'", weakCondition="$state = 'VIC'")
    assert attributes['resultClass'] == 'relaxedCondition'
    assert [label for label, _ in rows if label != 'null_row']


def test_condition_with_kwargs(handlers):
    """C11 - the condition parameters travel in kwargs down to the query."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=5,
                                    condition='$state = :st', st='NSW')
    assert [label for label, _ in rows if label != 'null_row']


def test_no_id_and_no_querystring_gives_the_bare_bag(handlers):
    """D3 - neither branch runs: no rows, no columns, no null row."""
    rows, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER)
    assert rows == []
    assert sorted(attributes) == ['resultClass']


# ---------------------------------------------------------------------------
#  D. applymethod, output and result attributes
# ---------------------------------------------------------------------------

def test_applymethod_merges_into_the_result_attributes(handlers):
    """D1, D8 - the applymethod result is merged into the attributes."""
    def applymethod(selection, **kwargs):
        return dict(extra='yes', rows=len(selection))
    for handler in handlers:
        handler.page.rpc_methods['myapply'] = applymethod
    _, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                          _querystring='Archer', limit=2,
                                          applymethod='myapply')
    assert attributes['extra'] == 'yes'
    assert attributes['rows'] == 2


def test_applymethod_receives_the_raw_kwargs(handlers):
    """D1 - the applymethod gets kwargs as they came, not the apply_ slice."""
    seen = []

    def applymethod(selection, **kwargs):
        seen.append(kwargs)
        return None
    for handler in handlers:
        handler.page.rpc_methods['myapply'] = applymethod
    _assert_same_dbselect(handlers, dbtable=CUSTOMER, _querystring='Archer',
                          limit=2, applymethod='myapply', apply_foo='bar')
    assert seen[0] == dict(apply_foo='bar')
    assert seen[1] == seen[0]


def test_applymethod_receives_none_when_no_branch_ran(handlers):
    """D2 - with neither _id nor querystring the applymethod gets None (DS2)."""
    seen = []

    def applymethod(selection, **kwargs):
        seen.append(selection)
        return dict(extra='yes')
    for handler in handlers:
        handler.page.rpc_methods['myapply'] = applymethod
    _assert_same_dbselect(handlers, dbtable=CUSTOMER, applymethod='myapply')
    assert seen == [None, None]


def test_applymethod_result_is_dropped_on_an_empty_selection(handlers):
    """D8 - an empty selection discards the applymethod result (DS4)."""
    def applymethod(selection, **kwargs):
        return dict(extra='yes')
    for handler in handlers:
        handler.page.rpc_methods['myapply'] = applymethod
    _, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                          _querystring='no such customer',
                                          applymethod='myapply')
    assert 'extra' not in attributes


def test_empty_result_has_no_columns_and_no_null_row(handlers):
    """D3 - an empty search gives a bare Bag, so no way to clear the field (DS3)."""
    rows, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                             _querystring='no such customer',
                                             emptyLabel='none')
    assert rows == []
    assert sorted(attributes) == ['resultClass']


def test_headers_use_name_short_then_label(handlers):
    """D6 - name_short wins over label, and every header goes through page._."""
    _, attributes = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                          _querystring='Archer', limit=2,
                                          auxColumns='$email')
    assert attributes['headers'] == 'Account name,!!Email'
    for handler in handlers:
        assert handler.page.translated == ['Account name', '!!Email']


def test_null_row(handlers):
    """D9 - the empty label row closes the Bag by default."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=2,
                                    emptyLabel='none', emptyLabel_class='xx')
    label, attributes = rows[-1]
    assert label == 'null_row'
    assert attributes['caption'] == 'none'
    assert attributes['_customClasses'] == 'xx'


def test_notnull_drops_the_null_row(handlers):
    """D9 - notnull suppresses the empty label row."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=2,
                                    notnull=True)
    assert [label for label, _ in rows if label == 'null_row'] == []


def test_empty_label_first(handlers):
    """D9 - emptyLabel_first puts the empty row at the top."""
    rows, _ = _assert_same_dbselect(handlers, dbtable=CUSTOMER,
                                    _querystring='Archer', limit=2,
                                    emptyLabel_first=True)
    assert rows[0][0] == 'null_row'


# ---------------------------------------------------------------------------
#  E. dbSelect_default — the four stages
# ---------------------------------------------------------------------------

def _search(handler, db, querystring, **pars):
    tblobj = db.table(CUSTOMER)
    pars.setdefault('limit', 5)
    selection = handler.dbSelect_default(tblobj, ['$account_name'], querystring,
                                         ['$account_name'], **pars)
    return [row['account_name'] for row in selection]


def _assert_same_search(handlers, db, querystring, **pars):
    legacy = _search(handlers[0], db, querystring, **pars)
    nxt = _search(handlers[1], db, querystring, **pars)
    assert nxt == legacy
    return legacy


def test_stage_contains(handlers, db, optranslate_spy):
    """E5, E9 - a first stage that does not fill the page is the only one."""
    calls = optranslate_spy(CUSTOMER)
    names = _assert_same_search(handlers, db, 'Archer', limit=50)
    assert names
    assert all('Archer' in name for name in names)
    assert [op for op, _ in calls] == ['contains', 'contains']


def test_stage_startswith(handlers, db, optranslate_spy):
    """E6 - a first stage that fills the page is narrowed by a startswith."""
    calls = optranslate_spy(CUSTOMER)
    names = _assert_same_search(handlers, db, 'Archer', limit=5)
    assert len(names) == 5
    assert all(name.startswith('Archer') for name in names)
    assert [op for op, _ in calls] == ['contains', 'startswith',
                                       'contains', 'startswith']


def test_stage_regex(handlers, db):
    """E7 - a star inside the query is found only by the regex stage.

    The regex stage strips the special characters out of the query string
    before it splits it, the other three do not, so ``Arch*er`` is the word
    ``Archer`` for the regex stage and a literal for the ILIKE one.  With the
    regex stage disabled this case comes back empty.
    """
    names = _assert_same_search(handlers, db, 'Arch*er')
    assert names
    assert all(name.startswith('Archer') for name in names)


def test_stage_regex_matches_the_words_out_of_order(handlers, db):
    """E7, E8 - the words in the wrong order are found, by regex or by ILIKE."""
    names = _assert_same_search(handlers, db, 'Baker Archer')
    assert names == ['Archer Baker']


def test_stage_ilike(handlers, db):
    """E8 - a fragment inside a word is found only by the ILIKE stage."""
    names = _assert_same_search(handlers, db, 'rche')
    assert names
    assert all('Archer' in name for name in names)


def test_empty_query_string_returns_everything(handlers, db):
    """E4 - an empty query string short-circuits to an unfiltered selection."""
    names = _assert_same_search(handlers, db, '', limit=3)
    assert len(names) == 3


def test_exclude_string(handlers, db):
    """E1, E2, E10 - a comma separated exclude is a NOT IN on the pkey."""
    tblobj = db.table(CUSTOMER)
    excluded = tblobj.query(columns='$account_name', where="$account_name LIKE 'Archer%'",
                            order_by='$account_name', limit=1).fetch()[0]
    names = _assert_same_search(handlers, db, 'Archer',
                                exclude=excluded['pkey'], limit=50)
    assert excluded['account_name'] not in names


def test_exclude_list_drops_the_none_entries(handlers, db):
    """E1 - an iterable exclude keeps only the truthy entries."""
    with_none = _assert_same_search(handlers, db, 'Archer',
                                    exclude=[None, 'no-such-pkey'], limit=5)
    plain = _assert_same_search(handlers, db, 'Archer',
                                exclude=['no-such-pkey'], limit=5)
    assert with_none == plain


def test_exclude_empty_is_ignored(handlers, db):
    """E1 - an empty exclude adds no condition."""
    empty = _assert_same_search(handlers, db, 'Archer', exclude='', limit=5)
    absent = _assert_same_search(handlers, db, 'Archer', limit=5)
    assert empty == absent


def test_a_where_keyword_is_discarded(handlers, db):
    """E3 - a where sent by the caller is popped out of the keywords."""
    with_where = _assert_same_search(handlers, db, 'Archer', limit=5,
                                     where='$account_name IS NULL')
    without = _assert_same_search(handlers, db, 'Archer', limit=5)
    assert with_where == without


def test_the_search_stages_no_longer_share_the_sqlargs(
        handlers, db, optranslate_spy):
    """E6 - EQUIVALENCE since the frozen handler was fixed (DS5).

    One sqlArgs dict was handed to both stages, so the second bound its value
    next to the label of a condition no longer being run. Each stage now gets
    a dict of its own in both handlers.
    """
    calls = optranslate_spy(CUSTOMER)
    legacy, nxt = handlers
    _search(legacy, db, 'Archer', limit=5)
    legacy_calls = list(calls)
    del calls[:]
    _search(nxt, db, 'Archer', limit=5)
    next_calls = list(calls)
    assert [op for op, _ in legacy_calls] == ['contains', 'startswith']
    assert [op for op, _ in next_calls] == ['contains', 'startswith']
    assert legacy_calls[0][1] == next_calls[0][1] == {}
    assert legacy_calls[1][1] == next_calls[1][1] == {}


def test_search_condition_is_anded_with_the_stage(handlers, db):
    """E9 - the stage condition and the caller condition are AND-ed."""
    names = _assert_same_search(handlers, db, 'Archer', limit=50,
                                condition="$state = 'NSW'")
    assert names
    assert all('Archer' in name for name in names)


# ---------------------------------------------------------------------------
#  F. tableAnalyzeStore
# ---------------------------------------------------------------------------

def _analyze(handler, **pars):
    store, timings = handler.tableAnalyzeStore(**pars)
    return [(node.label, dict(node.attr)) for node in store], sorted(timings)


def test_analyze_store_rows(handlers):
    """F1, F3, F6, F8 - same totalized rows and same timing keys."""
    legacy = _analyze(handlers[0], table=CUSTOMER, group_by=['$state'])
    nxt = _analyze(handlers[1], table=CUSTOMER, group_by=['$state'])
    assert nxt == legacy
    assert legacy[1] == ['query_time', 'resolver_load_time', 'totalize_time']
    assert legacy[0]


def test_analyze_store_with_a_where(handlers):
    """F3 - the where narrows the analyzed rows."""
    legacy = _analyze(handlers[0], table=CUSTOMER, group_by=['$state'],
                      where="$state = 'NSW'")
    nxt = _analyze(handlers[1], table=CUSTOMER, group_by=['$state'],
                   where="$state = 'NSW'")
    assert nxt == legacy
    assert len(legacy[0]) == 1


def test_analyze_store_ignores_the_callables_in_the_columns(handlers):
    """F2, F6 - a callable in group_by is not a column but is totalized."""
    def bucket(row):
        return (row['state'] or '')[:1]
    legacy = _analyze(handlers[0], table=CUSTOMER, group_by=['$state', bucket])
    nxt = _analyze(handlers[1], table=CUSTOMER, group_by=['$state', bucket])
    assert nxt == legacy
    assert legacy[0]


def test_analyze_store_writes_the_explorer_pickle(handlers):
    """F7 - the lazy bag is pickled under the page:explorer static location."""
    for handler in handlers:
        handler.tableAnalyzeStore(table=CUSTOMER, group_by=['$state'])
        path = os.path.join(handler.page.site.static_root, 'page_explorer',
                            'explorer-fixed-uuid.pik')
        assert os.path.exists(path)


# ---------------------------------------------------------------------------
#  G. getValuesString
# ---------------------------------------------------------------------------

def test_values_string_default_caption_field(handlers):
    """G2, G3, G4 - pkey:caption pairs, comma separated."""
    result = _assert_same_call(handlers, 'getValuesString', table='invc.state')
    assert result.split(',')[0] == 'NSW:NSW'


def test_values_string_with_a_caption_field(handlers):
    """G2 - an explicit caption field wins over the table attribute."""
    result = _assert_same_call(handlers, 'getValuesString', table='invc.state',
                               caption_field='name')
    assert result.split(',')[0] == 'NSW:New South Wales'


def test_values_string_alt_pkey(handlers):
    """G1 - alt_pkey_field replaces the pkey on the left of the colon."""
    result = _assert_same_call(handlers, 'getValuesString', table='invc.state',
                               alt_pkey_field='name', caption_field='code')
    assert result.split(',')[0] == 'New South Wales:NSW'


def test_values_string_with_a_where(handlers):
    """G3 - the keywords reach the query."""
    result = _assert_same_call(handlers, 'getValuesString', table='invc.state',
                               caption_field='name', where="$code = 'NSW'")
    assert result == 'NSW:New South Wales'


def test_values_string_replaces_the_commas(handlers, db):
    """G4 - a comma inside a caption becomes a space, on purpose."""
    pkey = _first_customer(db)
    result = _assert_same_call(handlers, 'getValuesString', table=CUSTOMER,
                               caption_field='full_address',
                               where='$id = :pk', pk=pkey)
    assert ',' not in result.split(':', 1)[1]


# ---------------------------------------------------------------------------
#  H. getMultiFetch
# ---------------------------------------------------------------------------

def _queries():
    bag = Bag()
    bag.setItem('first', None, table='invc.state', columns='$code,$name',
                where="$code = 'NSW'")
    bag.setItem('second', None, table='invc.region', columns='$code',
                limit=2)
    return bag


def test_multi_fetch_rows(handlers):
    """H3, H5 - one entry per node, keyed by the node label."""
    results = [handler.getMultiFetch(queries=_queries()) for handler in handlers]
    shapes = [[(node.label, [(row.label, dict(row.attr)) for row in node.value])
               for node in result] for result in results]
    assert shapes[1] == shapes[0]
    assert [label for label, _ in shapes[0]] == ['first', 'second']


@pytest.mark.parametrize('columns', [None, '*'])
def test_multi_fetch_star_columns(handlers, columns):
    """H3 - EQUIVALENCE since the frozen handler was fixed (DS7).

    ``columnsFromString('*')`` returns ``['$*']``, which reached the SELECT
    verbatim and the database rejected, so the documented default never
    worked, whether it was spelled out or left out. Both handlers now let
    ``'*'`` through unchanged.
    """
    def build():
        bag = Bag()
        attrs = dict(table='invc.region', limit=1)
        if columns:
            attrs['columns'] = columns
        bag.setItem('all', None, **attrs)
        return bag
    legacy, nxt = handlers
    legacy_result = legacy.getMultiFetch(queries=build())
    next_result = nxt.getMultiFetch(queries=build())
    for result in (legacy_result, next_result):
        assert 'name' in result['all'].getNode('#0').attr


def test_multi_fetch_leaves_the_caller_bag_alone(handlers):
    """H1 - EQUIVALENCE since the frozen handler was fixed (DS6).

    ``columns`` and ``table`` were popped off the caller's own node, so the
    caller got its Bag back stripped. Both handlers now take the copy first.
    """
    for handler in handlers:
        bag = _queries()
        handler.getMultiFetch(queries=bag)
        assert sorted(bag.getNode('first').attr) == ['columns', 'table', 'where']


def test_multi_fetch_without_a_table_raises(handlers):
    """H2 - a node without a table raises KeyError, with no default."""
    for handler in handlers:
        bag = Bag()
        bag.setItem('broken', None, columns='$code')
        with pytest.raises(KeyError):
            handler.getMultiFetch(queries=bag)


def test_multi_fetch_db_env_is_scoped(store_handlers, db_with_external_store):
    """H4 - the dbenv_ attributes are scoped to the single query."""
    database = db_with_external_store
    for handler in store_handlers:
        bag = Bag()
        bag.setItem('scoped', None, table='invc.region', columns='$code',
                    limit=1, dbenv_storename='extstore')
        result = handler.getMultiFetch(queries=bag)
        assert len(result['scoped']) == 1
        assert database.currentEnv.get('storename') is None
