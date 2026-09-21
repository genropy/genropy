"""Equivalence between the getRecord and related flows of the two handlers.

``GnrWebAppHandlerNext`` moves the table level part of ``getRecord``,
``getRelatedRecord`` and ``getRelatedSelection`` onto an app level table proxy
(``tblobj.recordProxy()``).  It is a refactoring, so every input must give
the same record Bag and the same recInfo through both handlers; the few
declared divergences are the defect fixes of ``bugs.md`` and each of them has
a test that asserts the divergence instead of the equality.

Every case below covers one row of the behaviour tables in
``.subtasks/alt-apphandler/progress.md``, step P3.1, named in its docstring.

The database, the stand-in page and the two handlers built on it come from
``apphandler_next_common``, shared with ``test_apphandler_next.py``.
"""

import datetime

import pytest

from gnr.core.gnrbag import Bag

from apphandler_next_common import normalized_attributes
# pytest resolves fixtures by name in the module namespace, so the shared ones
# are imported even though nothing in this file calls them.
from apphandler_next_common import (gnr_test_config, db, db_postgres,  # noqa: F401
                                    make_handlers, handlers, pg_handlers)


# ---------------------------------------------------------------------------
#  Comparison helpers
# ---------------------------------------------------------------------------

def _record_shape(record):
    """The comparable shape of a record Bag.

    ``getStaticValue`` is used instead of the value so that a lazy relation
    resolver is not fired by the comparison itself: an eager relation, which
    the flow resolves on purpose, comes back as a Bag and is compared again.
    """
    shape = []
    for node in record:
        value = node.getStaticValue()
        if isinstance(value, Bag):
            value = _record_shape(value)
        elif not isinstance(value, (str, int, float, bool, type(None),
                                    datetime.date, datetime.datetime)):
            value = type(value).__name__
        shape.append((node.label, dict(node.attr), value))
    return shape


def _normalized_record(result, ignore=()):
    record, recInfo = result
    return _record_shape(record), normalized_attributes(recInfo, ignore=ignore)


def _assert_same_record(handlers, _ignore=(), _method='getRecord', **pars):
    """Run the same call through both handlers and compare record and recInfo."""
    legacy, nxt = handlers
    legacy_shape, legacy_info = _normalized_record(
        getattr(legacy, _method)(**pars), ignore=_ignore)
    next_shape, next_info = _normalized_record(
        getattr(nxt, _method)(**pars), ignore=_ignore)
    assert next_shape == legacy_shape
    assert next_info == legacy_info
    return legacy_shape, legacy_info


def _assert_same_selection(handlers, _ignore=(), **pars):
    """Run getRelatedSelection through both handlers and compare the output."""
    legacy, nxt = handlers
    results = []
    for handler in (legacy, nxt):
        rows, attributes = handler.getRelatedSelection(**pars)
        results.append(([(node.label, dict(node.attr)) for node in rows],
                        normalized_attributes(attributes, ignore=_ignore)))
    assert results[1] == results[0]
    return results[0]


# ---------------------------------------------------------------------------
#  Data helpers
# ---------------------------------------------------------------------------

def _first_customer(db):
    return db.table('invc.customer').query(
        columns='$id', order_by='$id', limit=1).fetch()[0]['id']


def _first_invoice(db):
    return db.table('invc.invoice').query(
        columns='$id,$customer_id', order_by='$id', limit=1).fetch()[0]


def _clone_customer(db, **changes):
    """Insert a copy of the first customer, with *changes* applied."""
    tblobj = db.table('invc.customer')
    source = dict(tblobj.record(pkey=_first_customer(db)).output('dict'))
    for key in list(source):
        if key.startswith('__') or key == 'id':
            source.pop(key)
    source.update(changes)
    record = tblobj.newrecord(**source)
    tblobj.insert(record)
    db.commit()
    return record['id']


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
def table_method(db):
    """Attach a method to a table instance for the duration of one test."""
    restore = []

    def setter(table, name, method):
        tblobj = db.table(table)
        restore.append((tblobj, name, name in tblobj.__dict__,
                        tblobj.__dict__.get(name)))
        setattr(tblobj, name, method)
    yield setter
    for tblobj, name, existed, old in reversed(restore):
        if existed:
            setattr(tblobj, name, old)
        else:
            delattr(tblobj, name)


# ---------------------------------------------------------------------------
#  getRecord — table resolution, pkey and lock
# ---------------------------------------------------------------------------

def test_record_by_pkey(handlers, db):
    """R3, R13 - the plain read: same record Bag and same recInfo."""
    shape, info = _assert_same_record(handlers, table='invc.customer',
                                      pkey=_first_customer(db))
    assert shape
    assert info['_newrecord'] is False
    assert info['table'] == 'invc.customer'


def test_pkg_prefixes_the_table(handlers, db):
    """R2 - ``pkg`` is prepended to ``dbtable``."""
    _assert_same_record(handlers, dbtable='customer', pkg='invc',
                        pkey=_first_customer(db))


def test_logical_table_is_what_the_handler_sees(handlers, db):
    """R2, R15, R30 - the onLoading handler sees ``table``, the client
    receives ``dbtable``.  The overwrite at get_record.py:278 is after every
    handler, and that ordering is load bearing."""
    seen = []
    for handler in handlers:
        handler.page.rpc_methods['probe'] = (
            lambda record, newrecord, loadingParameters, recInfo:
            seen.append(recInfo.get('table')))
    _, info = _assert_same_record(handlers, table='LOGICAL',
                                  dbtable='invc.customer',
                                  pkey=_first_customer(db),
                                  onLoadingHandler='probe')
    assert seen == ['LOGICAL', 'LOGICAL']
    assert info['table'] == 'invc.customer'


def test_lock_without_pkey_is_downgraded(handlers, db):
    """R4 - a record selected by a column instead of a pkey: the lock is
    silently turned off, so ``for_update`` never reaches the query."""
    caption = db.table('invc.customer').record(
        pkey=_first_customer(db)).output('dict')['account_name']
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  account_name=caption, lock=True)
    assert info['_pkey'] == _first_customer(db)


def test_lock_with_pkey(handlers, db):
    """R5, R17 - ``for_update`` is injected and ``_getRecord_locked`` runs;
    the lock helper is inert, so nothing reaches recInfo."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db), lock=True)
    assert 'lockId' not in info


# ---------------------------------------------------------------------------
#  getRecord — columns, output modes and pkey re-derivation
# ---------------------------------------------------------------------------

def test_virtual_columns_carry_the_caption_columns(handlers, db):
    """R8 - the caption columns are added to the requested virtual columns."""
    shape, _ = _assert_same_record(handlers, table='invc.customer',
                                   pkey=_first_customer(db),
                                   virtual_columns='n_invoices')
    labels = [row[0] for row in shape]
    assert 'n_invoices' in labels
    assert 'account_name' in labels


def test_new_record(handlers):
    """R11, R26 - ``*newrecord*`` gives a blank record; ``lastTS`` is the
    string ``'None'`` because line 269 calls ``str()`` on a missing value."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey='*newrecord*')
    assert info['_pkey'] == '*newrecord*'
    assert info['_newrecord'] is True
    assert info['lastTS'] == 'None'


def test_sample_record_returns_early(handlers):
    """R12 - ``*sample*`` returns before everything else: two keys only."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey='*sample*')
    assert info == dict(_pkey='*sample*', caption='!!Sample data')


def test_missing_pkey_becomes_a_new_record(handlers):
    """R14 - a pkey that matches no row produces a blank record."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey='no_such_pkey')
    assert info['_pkey'] == '*newrecord*'
    assert info['_newrecord'] is True


def test_protection_flags(handlers, db):
    """R16 - an existing record read read-write carries the two flags."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db))
    assert info['_protect_write'] is False
    assert info['_protect_delete'] is False


def test_read_only_skips_the_protection_flags(handlers, db):
    """R16 - ``readOnly`` skips the four table calls and the two flags."""
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db), readOnly=True)
    assert '_protect_write' not in info
    assert '_protect_delete' not in info


# ---------------------------------------------------------------------------
#  getRecord — handlers and defaults
# ---------------------------------------------------------------------------

def test_loading_parameters_dict_is_mutated(handlers, db):
    """R18, R21 - the caller's dict is updated with the defaults and loses
    its ``method`` key, in place."""
    seen = []
    for handler in handlers:
        loadingParameters = dict(method='probe', extra='keep')
        handler.page.rpc_methods['probe'] = (
            lambda record, newrecord, lp, recInfo: None)
        handler.getRecord(table='invc.customer', pkey=_first_customer(db),
                          loadingParameters=loadingParameters, default_state='NSW')
        seen.append(loadingParameters)
    assert seen[0] == seen[1] == dict(extra='keep', state='NSW')


def test_on_loading_handler_explicit(handlers, db):
    """R21 - an explicit ``onLoadingHandler`` wins over every other route."""
    for handler in handlers:
        handler.page.maintable = 'invc.customer'
        handler.page.onLoading = (
            lambda record, newrecord, lp, recInfo: recInfo.update(via='maintable'))
        handler.page.rpc_methods['explicit'] = (
            lambda record, newrecord, lp, recInfo: recInfo.update(via='explicit'))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db),
                                  onLoadingHandler='explicit')
    assert info['via'] == 'explicit'


def test_on_loading_method_key(handlers, db):
    """R21 - ``loadingParameters['method']`` is the fallback handler name.

    Each handler gets its own dict because line 237 pops the key out of the
    caller's dict in place (R18): sharing one dict would leave the second
    handler without a handler name.
    """
    seen = []
    for handler in handlers:
        handler.page.rpc_methods['by_key'] = (
            lambda record, newrecord, lp, recInfo: recInfo.update(via='by_key'))
        _, info = handler.getRecord(table='invc.customer',
                                    pkey=_first_customer(db),
                                    loadingParameters=dict(method='by_key'))
        seen.append(info['via'])
    assert seen == ['by_key', 'by_key']


def test_maintable_uses_on_loading(handlers, db):
    """R21 - when the table is the page maintable the handler is ``onLoading``."""
    for handler in handlers:
        handler.page.maintable = 'invc.customer'
        handler.page.onLoading = (
            lambda record, newrecord, lp, recInfo: recInfo.update(via='onLoading'))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db))
    assert info['via'] == 'onLoading'


def test_related_table_uses_on_loading_related_method(handlers, db):
    """R21 - any other table goes through ``page.onLoadingRelatedMethod``."""
    for handler in handlers:
        handler.page.maintable = 'invc.invoice'
        handler.page.onLoading_invc_customer = (
            lambda record, newrecord, lp, recInfo: recInfo.update(via='related'))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db))
    assert info['via'] == 'related'


def test_table_onloading_runs_before_defaults(handlers, table_method):
    """R19, R22 - ``tblobj.onLoading`` sees the record before the defaults."""
    seen = []

    def onLoading(record, newrecord, loadingParameters, recInfo):
        seen.append(record['state'])
    table_method('invc.customer', 'onLoading', onLoading)
    shape, _ = _assert_same_record(handlers, table='invc.customer',
                                   pkey='*newrecord*', default_state='NSW')
    assert seen == [None, None]
    assert dict((row[0], row[2]) for row in shape)['state'] == 'NSW'


def test_table_onloading_star_runs_after_defaults(handlers, table_method):
    """R20, R22 - the ``onLoading_*`` table handlers see the defaults."""
    seen = []

    def onLoading_probe(record, newrecord, loadingParameters, recInfo):
        seen.append(record['state'])
    table_method('invc.customer', 'onLoading_probe', onLoading_probe)
    _assert_same_record(handlers, table='invc.customer', pkey='*newrecord*',
                        default_state='NSW')
    assert seen == ['NSW', 'NSW']


def test_defaults_with_a_handler(handlers, table_method):
    """R22 - with a handler the defaults come from ``default_kwargs`` only."""
    table_method('invc.customer', 'onLoading_probe',
                 lambda record, newrecord, lp, recInfo: None)
    shape, _ = _assert_same_record(handlers, table='invc.customer',
                                   pkey='*newrecord*', default_state='NSW',
                                   loadingParameters=dict(suburb='Ignored'))
    values = dict((row[0], row[2]) for row in shape)
    assert values['state'] == 'NSW'
    assert values['suburb'] is None


def test_defaults_without_a_handler(handlers):
    """R23 - with no handler the defaults come from ``loadingParameters``,
    which line 229 has already merged with ``default_kwargs``."""
    shape, _ = _assert_same_record(handlers, table='invc.customer',
                                   pkey='*newrecord*', default_state='NSW',
                                   loadingParameters=dict(suburb='Applied'))
    values = dict((row[0], row[2]) for row in shape)
    assert values['state'] == 'NSW'
    assert values['suburb'] == 'Applied'


def test_defaults_unknown_key_is_seeded_with_none(handlers):
    """R23 - a default whose key the record has not got is added as ``None``,
    which is why ``setRecordDefaults`` can then set it."""
    shape, _ = _assert_same_record(handlers, table='invc.customer',
                                   pkey='*newrecord*', default_no_such_field='x')
    values = dict((row[0], row[2]) for row in shape)
    assert values['no_such_field'] == 'x'


def test_set_record_defaults_skips_absent_keys(handlers, db):
    """R22 - ``setRecordDefaults`` writes only the keys already in the record."""
    for handler in handlers:
        record = Bag()
        record['state'] = None
        handler.setRecordDefaults(db.table('invc.customer'), record,
                                  dict(state='NSW', not_a_column='x'))
        assert record['state'] == 'NSW'
        assert 'not_a_column' not in record


# ---------------------------------------------------------------------------
#  getRecord — applymethod, status flags, counters, caption
# ---------------------------------------------------------------------------

def test_applymethod_merges_into_recinfo(handlers, db):
    """R24 - the ``apply_*`` kwargs and the fixed ones reach the method, and
    a truthy result is merged into recInfo."""
    seen = []
    for handler in handlers:
        handler.page.rpc_methods['ap'] = (
            lambda record, **pars: seen.append(sorted(pars)) or dict(extra=1))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db), applymethod='ap',
                                  apply_z=3, subtable='residential')
    assert info['extra'] == 1
    assert seen[0] == ['loadingParameters', 'newrecord', 'recInfo', 'subtable',
                       'tblobj', 'z']


def test_applymethod_cannot_override_caption(handlers, db):
    """R24, R33 - the merge is before the caption, so the caption wins."""
    for handler in handlers:
        handler.page.rpc_methods['ap'] = (
            lambda record, **pars: dict(caption='forced', _pkey='forced'))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db), applymethod='ap')
    assert info['caption'] != 'forced'
    assert info['_pkey'] == 'forced'


def test_draft_record(handlers, db):
    """R28 - a draft row carries ``_draft``."""
    pkey = _clone_customer(db, account_name='Draft Co', __is_draft=True)
    _, info = _assert_same_record(handlers, table='invc.customer', pkey=pkey)
    assert info['_draft'] is True


def test_logically_deleted_record(handlers, db):
    """R27 - a logically deleted row carries ``_logical_deleted``."""
    pkey = _clone_customer(db, account_name='Deleted Co',
                           __del_ts=datetime.datetime(2026, 1, 1, 12, 0))
    _, info = _assert_same_record(handlers, table='invc.customer', pkey=pkey)
    assert info['_logical_deleted'] is True


def test_invalid_fields(handlers, db, table_attribute):
    """R29 - the column named by the ``invalidFields`` table attribute is read
    back from JSON into ``_invalidFields``."""
    pkey = _clone_customer(db, account_name='Invalid Co',
                           notes='{"account_name": "too short"}')
    table_attribute('invc.customer', 'invalidFields', 'notes')
    _, info = _assert_same_record(handlers, table='invc.customer', pkey=pkey)
    assert info['_invalidFields'] == {'account_name': 'too short'}


def test_counter_column_on_a_new_record(handlers):
    """R32 - a new invoice gets the promised counter written in the record."""
    shape, _ = _assert_same_record(handlers, table='invc.invoice',
                                   pkey='*newrecord*')
    row = [r for r in shape if r[0] == 'inv_number'][0]
    assert row[2]
    assert row[1]['promised'] is True


def test_counter_column_skipped_when_from_fld(handlers):
    """R32 - a record loaded as the target of a relation gets no counter."""
    shape, _ = _assert_same_record(handlers, table='invc.invoice',
                                   pkey='*newrecord*',
                                   from_fld='invc.invoice_row.invoice_id')
    row = [r for r in shape if r[0] == 'inv_number'][0]
    assert row[2] is None


def test_caption_sees_the_handler_mutations(handlers, db, table_method):
    """R33 - the caption is computed last, on the mutated record."""
    table_method('invc.customer', 'onLoading_probe',
                 lambda record, newrecord, lp, recInfo:
                 record.setItem('account_name', 'Renamed by the handler'))
    _, info = _assert_same_record(handlers, table='invc.customer',
                                  pkey=_first_customer(db))
    assert info['caption'] == 'Renamed by the handler'


# ---------------------------------------------------------------------------
#  getRecord — SQL context and eager relations
# ---------------------------------------------------------------------------

def _install_sql_context(handlers, path, joinbag):
    for handler in handlers:
        handler.page.pageStore().setItem('_sqlctx.conditions.%s' % path, joinbag)


def test_get_record_with_sql_context(handlers, db):
    """R10 - the join conditions of a SQL context are applied to the record."""
    joinbag = Bag(dict(target_fld='invc.customer.state', from_fld='invc.state.code',
                       condition='$name = :sname', one_one=False, applymethod=None,
                       params=Bag(dict(sname='New South Wales'))))
    _install_sql_context(handlers, 'ctx.invc_customer_state_invc_state_code',
                         joinbag)
    _assert_same_record(handlers, table='invc.customer',
                        pkey=_first_customer(db), sqlContextName='ctx')


def test_eager_relation_is_expanded(handlers, db):
    """R31 - an ``_eager_one`` node is replaced by the loaded related record."""
    invoice = _first_invoice(db)
    resolved = []
    for handler in handlers:
        record, _ = handler.getRecord(table='invc.invoice', pkey=invoice['id'])
        node = record.getNode('@customer_id')
        node.attr['_eager_one'] = True
        handler._handleEagerRelations(record, 0, _eager_record_stack=[])
        resolved.append((node.getStaticValue()['account_name'],
                         node.attr['_resolvedInfo']['_pkey']))
    assert resolved[0] == resolved[1]
    assert resolved[0][1] == invoice['customer_id']


def test_eager_weak_is_expanded_only_at_level_zero(handlers, db):
    """R31 - ``_eager_one == 'weak'`` fires at level 0 and nowhere else."""
    invoice = _first_invoice(db)
    for level, expanded in ((0, True), (1, False)):
        seen = []
        for handler in handlers:
            record, _ = handler.getRecord(table='invc.invoice', pkey=invoice['id'])
            node = record.getNode('@customer_id')
            node.attr['_eager_one'] = 'weak'
            handler._handleEagerRelations(record, level, _eager_record_stack=[])
            seen.append('_resolvedInfo' in node.attr)
        assert seen == [expanded, expanded]


def test_eager_resolver_kwargs_are_rewritten(handlers, db):
    """R31 - a resolver kwarg starting with ``=.`` is read from the record,
    and one starting with ``=`` without a dot silently becomes ``None``."""
    invoice = _first_invoice(db)
    seen = []
    for handler in handlers:
        record, _ = handler.getRecord(table='invc.invoice', pkey=invoice['id'])
        node = record.getNode('@customer_id')
        node.attr['_eager_one'] = True
        node.attr['_resolver_kwargs'] = dict(from_record='=.inv_number',
                                             from_client='=some.client.path',
                                             plain='literal')
        handler._handleEagerRelations(record, 0, _eager_record_stack=[])
        seen.append(dict(node.attr['_resolver_kwargs']))
    assert seen[0] == seen[1]
    assert seen[0]['from_client'] is None
    assert seen[0]['plain'] == 'literal'
    assert seen[0]['from_record']


# ---------------------------------------------------------------------------
#  getRelatedRecord
# ---------------------------------------------------------------------------

def test_related_record_by_pkey(handlers, db):
    """L1, L5 - the target table comes from ``target_fld``."""
    invoice = _first_invoice(db)
    _, info = _assert_same_record(handlers, _method='getRelatedRecord',
                                  from_fld='invc.invoice.customer_id',
                                  target_fld='invc.customer.id',
                                  pkey=invoice['customer_id'])
    assert info['_pkey'] == invoice['customer_id']
    assert info['table'] == 'invc.customer'
    assert info['from_fld'] == 'invc.invoice.customer_id'


def test_related_record_by_relation_value(handlers, db):
    """L2 - with no pkey the FK travels under the target table's pkey name."""
    invoice = _first_invoice(db)
    _, info = _assert_same_record(handlers, _method='getRelatedRecord',
                                  from_fld='invc.invoice.customer_id',
                                  target_fld='invc.customer.id',
                                  id=invoice['customer_id'])
    assert info['_pkey'] == invoice['customer_id']


def test_related_record_without_value_is_a_new_record(handlers):
    """L3 - a missing FK silently yields a blank record."""
    _, info = _assert_same_record(handlers, _method='getRelatedRecord',
                                  from_fld='invc.invoice.customer_id',
                                  target_fld='invc.customer.id')
    assert info['_pkey'] == '*newrecord*'


def test_related_record_pkg_parameter_is_not_used(handlers, db):
    """L1 - the ``pkg`` parameter of the signature is accepted and ignored:
    the package comes from ``target_fld``."""
    invoice = _first_invoice(db)
    _, info = _assert_same_record(handlers, _method='getRelatedRecord',
                                  from_fld='invc.invoice.customer_id',
                                  target_fld='invc.customer.id',
                                  pkg='no_such_package',
                                  pkey=invoice['customer_id'])
    assert info['table'] == 'invc.customer'


def test_related_record_resolver_kwargs_reach_loading_parameters(handlers, db):
    """L4 - ``resolver_kwargs`` are merged into ``loadingParameters``."""
    invoice = _first_invoice(db)
    seen = []
    for handler in handlers:
        handler.page.rpc_methods['probe'] = (
            lambda record, newrecord, lp, recInfo: seen.append(dict(lp)))
        handler.getRelatedRecord(from_fld='invc.invoice.customer_id',
                                 target_fld='invc.customer.id',
                                 pkey=invoice['customer_id'],
                                 resolver_kwargs=dict(probe_key='probe_value'),
                                 loadingParameters=dict(method='probe'))
    assert seen[0] == seen[1] == dict(probe_key='probe_value')


def test_related_record_sql_context_applymethod(handlers, db):
    """L6 - the applymethod of a SQL context join condition runs after
    getRecord and its return value is discarded."""
    invoice = _first_invoice(db)
    joinbag = Bag(dict(target_fld='invc.customer.id',
                       from_fld='invc.invoice.customer_id',
                       condition=None, one_one=False, applymethod='ap',
                       params=Bag()))
    _install_sql_context(
        handlers, 'ctx2.invc_customer_id_invc_invoice_customer_id', joinbag)
    seen = []
    for handler in handlers:
        handler.page.rpc_methods['ap'] = (
            lambda record, **pars: seen.append(pars) or dict(discarded=True))
    _, info = _assert_same_record(handlers, _method='getRelatedRecord',
                                  from_fld='invc.invoice.customer_id',
                                  target_fld='invc.customer.id',
                                  pkey=invoice['customer_id'],
                                  sqlContextName='ctx2', apply_flag='on')
    assert seen[0] == seen[1] == dict(flag='on')
    assert 'discarded' not in info


# ---------------------------------------------------------------------------
#  getRelatedSelection
# ---------------------------------------------------------------------------

def test_related_selection_rows(handlers, db):
    """S5, S12, S14 - one node per related row, keyed by its pkey."""
    invoice = _first_invoice(db)
    rows, attributes = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'])
    assert rows
    assert attributes['dbtable'] == 'invc.invoice_row'
    assert attributes['totalrows'] == len(rows)
    label, attr = rows[0]
    assert attr['_pkey'] == label
    assert attr['_target_fld'] == 'invc.invoice_row.id'
    assert attr['_from_fld'] == ''


def test_related_selection_without_relation_value(handlers):
    """S6 - a falsy relation value forces ``limit=0``: no rows, no error."""
    rows, attributes = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id', relation_value=None)
    assert rows == []
    assert attributes['totalrows'] == 0


def test_related_selection_condition(handlers, db):
    """S7 - ``condition`` becomes the WHERE of the related query."""
    invoice = _first_invoice(db)
    rows, _ = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'], condition='$quantity > :qmin', qmin=0)
    assert rows


def test_related_selection_ignores_the_columns_parameter(handlers, db):
    """D19 - ``columns`` is assigned three times and never read, so every
    column specification gives the same payload.  Both handlers reproduce it."""
    invoice = _first_invoice(db)
    payloads = set()
    for columns in ('$product_id', '*', ''):
        _, attributes = _assert_same_selection(
            handlers, from_fld='invc.invoice.id',
            target_fld='invc.invoice_row.invoice_id',
            relation_value=invoice['id'], columns=columns)
        payloads.add(attributes['childResolverParams'])
    assert len(payloads) == 1
    assert '"quantity": null' in payloads.pop()


def test_related_selection_query_columns_fallback(handlers, db):
    """S1 - ``query_columns`` is logged as unexpected and then used anyway.
    Since D19 makes ``columns`` inert, the only observable effect is the log."""
    invoice = _first_invoice(db)
    rows, _ = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'], query_columns='$quantity')
    assert rows


def test_related_selection_child_resolver_params(handlers, db):
    """S11, S13 - ``childResolverParams`` lists every column of the selection,
    because line 230 extends ``relOneParams`` after the row loop."""
    invoice = _first_invoice(db)
    rows, attributes = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'])
    payload = attributes['childResolverParams']
    assert payload.endswith('::JS')
    assert '"quantity": null' in payload
    assert set(rows[0][1]) >= {'_pkey', '_relation_value', '_target_fld',
                               '_from_fld', '_resolver_name', '_sqlContextName'}


def test_related_selection_newproc_is_always_no(handlers, db):
    """D3 - ``getattr(self, 'self.newprocess', 'no')`` reads an attribute whose
    name is the literal dotted string, so the value is the constant ``'no'``.
    Reproduced in Next for the same reason as E5 of the getSelection flow."""
    invoice = _first_invoice(db)
    for handler in handlers:
        handler.newprocess = 'yes'
        _, attributes = handler.getRelatedSelection(
            from_fld='invc.invoice.id',
            target_fld='invc.invoice_row.invoice_id',
            relation_value=invoice['id'])
        assert attributes['newproc'] == 'no'


def test_related_selection_sql_context_condition(handlers, db):
    """S9 - the join condition of the SQL context is applied to the query and
    re-applied on the wildcard pair, which puts it on the root of the WHERE.

    The re-applied condition reaches the SQL uncompiled — the WHERE ends with
    ``AND ( $quantity > :qmin )``, with ``$quantity`` never turned into a
    column reference (defect D20, in the query layer, out of the scope of this
    subtask).  On sqlite that selects nothing.  Both handlers do it the same
    way, which is what this case asserts.
    """
    invoice = _first_invoice(db)
    joinbag = Bag(dict(target_fld='invc.invoice_row.invoice_id',
                       from_fld='invc.invoice.id',
                       condition='$quantity > :qmin', one_one=False,
                       applymethod=None, params=Bag(dict(qmin=0))))
    _install_sql_context(
        handlers, 'ctx3.invc_invoice_row_invoice_id_invc_invoice_id', joinbag)
    without_context, _ = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'])
    with_context, _ = _assert_same_selection(
        handlers, from_fld='invc.invoice.id',
        target_fld='invc.invoice_row.invoice_id',
        relation_value=invoice['id'], sqlContextName='ctx3')
    assert without_context
    assert with_context == []


# ---------------------------------------------------------------------------
#  Declared divergence: D2
# ---------------------------------------------------------------------------

def test_related_selection_sql_context_applymethod_diverges(handlers, db):
    """D2 - ``related.py:202`` resets ``joinBag`` to ``None`` right after
    line 192 filled it, so the applymethod branch at 211-215 can never run:
    an applymethod declared on a SQL context join condition is honoured by
    ``getRelatedRecord`` and silently dropped by ``getRelatedSelection``.

    Fixed in Next, which keeps the value read at 192.  This case asserts the
    divergence: legacy never calls the method, Next calls it once and merges
    its result into the result attributes.
    """
    invoice = _first_invoice(db)
    joinbag = Bag(dict(target_fld='invc.invoice_row.invoice_id',
                       from_fld='invc.invoice.id',
                       condition=None, one_one=False, applymethod='ap',
                       params=Bag()))
    _install_sql_context(
        handlers, 'ctx4.invc_invoice_row_invoice_id_invc_invoice_id', joinbag)
    calls = {}
    outcome = {}
    for name, handler in zip(('legacy', 'next'), handlers):
        handler.page.rpc_methods['ap'] = (
            lambda selection, _n=name, **pars:
            calls.setdefault(_n, []).append(pars) or dict(applied=_n))
        rows, attributes = handler.getRelatedSelection(
            from_fld='invc.invoice.id',
            target_fld='invc.invoice_row.invoice_id',
            relation_value=invoice['id'], sqlContextName='ctx4',
            apply_flag='on')
        outcome[name] = (len(rows), attributes.get('applied'))
    assert calls == {'next': [dict(flag='on')]}
    assert outcome['legacy'][1] is None
    assert outcome['next'][1] == 'next'
    assert outcome['legacy'][0] == outcome['next'][0]
