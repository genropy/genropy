"""Tests for sys.counter and sys.counter_block: counter numbers kept as blocks.

The counter is ``invc.invoice.inv_number`` of the test_invoice project
(format ``$K$YY/$NNNNNN``, code ``A``, ``date_field='date'``,
``recycle=True``). The tests enable the experimental switch
``new_counters/counters`` in the application config and give the counter an
``order_field``, which the new model requires to recycle. Each test works on
its own year, so on its own period. Order keys of a date are YYYYMMDD.
Runs on SQLite and PostgreSQL.
"""

import datetime

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException

from core.common import BaseGnrTest

COUNTER = 'invc.invoice.inv_number'


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(params=['db_sqlite', 'db_pg'])
def db(request):
    return request.getfixturevalue(request.param)


def _counter_pars(**extra):
    def counter_inv_number(record=None):
        pars = dict(format='$K$YY/$NNNNNN', code='A', period='YY', date_field='date',
                    showOnLoad=True, recycle=True)
        pars.update(extra)
        return pars
    return counter_inv_number


def _set_switch(db, value):
    config = db.application.config
    previous = config.getNode('experimental')
    experimental = Bag(previous.value) if previous and isinstance(previous.value, Bag) else Bag()
    if value is None:
        experimental.pop('new_counters')
    else:
        experimental.setItem('new_counters', None, counters=value)
    config.setItem('experimental', experimental)
    return previous


@pytest.fixture
def switch(db, monkeypatch):
    """Enables the new model for the invoice counter; returns a setter for its pars"""
    previous = _set_switch(db, COUNTER)
    invoice = db.table('invc.invoice')

    def set_pars(**extra):
        monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(**extra), raising=False)

    set_pars(order_field='date')
    yield set_pars
    config = db.application.config
    if previous is not None:
        config.setItem('experimental', previous.value, **previous.attr)
    else:
        config.pop('experimental')
    db.rollback()


def _insert(db, day, **kwargs):
    record = dict(date=day, **kwargs)
    db.table('invc.invoice').insert(record)
    db.commit()
    return record


def _blocks(db, year):
    rows = db.table('sys.counter_block').query(
        columns='$block_start,$block_end,$occupied,$order_first,$order_last',
        where='@counter_codekey.tbl=:t AND $period=:p', t='invoice', p=str(year),
        order_by='$block_start', addPkeyColumn=False).fetch()
    return [(r['block_start'], r['block_end'], bool(r['occupied']), r['order_first'], r['order_last'])
            for r in rows]


def _delete(db, record):
    invoice = db.table('invc.invoice')
    invoice.delete(invoice.record(record['id'], mode='record'))
    db.commit()


def d(year, month, day):
    return datetime.date(year, month, day)


def k(year, month, day):
    return year * 10000 + month * 100 + day


def test_new_numbers_make_one_occupied_block(db, switch):
    records = [_insert(db, d(2041, 1, n)) for n in (10, 11, 12)]
    assert [r['inv_number'] for r in records] == ['A41/000001', 'A41/000002', 'A41/000003']
    assert _blocks(db, 2041) == [(1, 3, True, k(2041, 1, 10), k(2041, 1, 12))]


def test_release_in_the_middle_leaves_a_free_block_with_its_window(db, switch):
    records = [_insert(db, d(2042, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    assert _blocks(db, 2042) == [(1, 1, True, k(2042, 1, 10), k(2042, 1, 10)),
                                 (2, 2, False, k(2042, 1, 10), k(2042, 1, 12)),
                                 (3, 3, True, k(2042, 1, 12), k(2042, 1, 12))]


def test_a_free_number_is_recycled_only_inside_its_window(db, switch):
    records = [_insert(db, d(2043, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    assert _insert(db, d(2043, 1, 20))['inv_number'] == 'A43/000004'
    assert _insert(db, d(2043, 1, 11))['inv_number'] == 'A43/000002'
    assert _blocks(db, 2043) == [(1, 4, True, k(2043, 1, 10), k(2043, 1, 20))]


def test_release_inside_a_long_block_reads_the_new_edges(db, switch):
    records = [_insert(db, d(2044, 2, n)) for n in (1, 2, 3, 4, 5)]
    _delete(db, records[2])
    assert _blocks(db, 2044) == [(1, 2, True, k(2044, 2, 1), k(2044, 2, 2)),
                                 (3, 3, False, k(2044, 2, 2), k(2044, 2, 4)),
                                 (4, 5, True, k(2044, 2, 4), k(2044, 2, 5))]


def test_release_of_the_last_number_takes_the_period_back(db, switch):
    records = [_insert(db, d(2045, 3, n)) for n in (1, 2, 3)]
    _delete(db, records[1])
    _delete(db, records[2])
    assert _blocks(db, 2045) == [(1, 1, True, k(2045, 3, 1), k(2045, 3, 1))]
    assert _insert(db, d(2045, 3, 9))['inv_number'] == 'A45/000002'


def test_a_number_set_by_hand_beyond_the_last_leaves_the_numbers_between_free(db, switch):
    _insert(db, d(2046, 4, 1))
    _insert(db, d(2046, 4, 5), inv_number='A46/000004')
    assert _blocks(db, 2046) == [(1, 1, True, k(2046, 4, 1), k(2046, 4, 1)),
                                 (2, 3, False, k(2046, 4, 1), k(2046, 4, 5)),
                                 (4, 4, True, k(2046, 4, 5), k(2046, 4, 5))]
    assert _insert(db, d(2046, 4, 3))['inv_number'] == 'A46/000002'


def test_a_number_set_by_hand_is_refused_when_in_use_or_out_of_its_window(db, switch):
    records = [_insert(db, d(2047, 5, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    with pytest.raises(GnrSqlBusinessLogicException):
        _insert(db, d(2047, 5, 13), inv_number='A47/000003')
    db.rollback()
    with pytest.raises(GnrSqlBusinessLogicException):
        _insert(db, d(2047, 5, 20), inv_number='A47/000002')
    db.rollback()
    assert _insert(db, d(2047, 5, 11), inv_number='A47/000002')['inv_number'] == 'A47/000002'


def test_a_value_that_is_not_a_number_of_the_series_is_left_alone(db, switch):
    _insert(db, d(2048, 6, 1))
    _insert(db, d(2048, 6, 2), inv_number='MANUAL-48')
    assert _blocks(db, 2048) == [(1, 1, True, k(2048, 6, 1), k(2048, 6, 1))]


def test_changing_the_number_releases_the_old_one(db, switch):
    records = [_insert(db, d(2049, 7, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with invoice.recordToUpdate(records[2]['id']) as record:
        record['inv_number'] = 'A49/000005'
    db.commit()
    assert _blocks(db, 2049) == [(1, 2, True, k(2049, 7, 1), k(2049, 7, 2)),
                                 (3, 4, False, k(2049, 7, 2), k(2049, 7, 3)),
                                 (5, 5, True, k(2049, 7, 3), k(2049, 7, 3))]


def test_a_number_moved_after_a_later_date_is_refused(db, switch):
    records = [_insert(db, d(2050, 7, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with pytest.raises(GnrSqlBusinessLogicException):
        with invoice.recordToUpdate(records[1]['id']) as record:
            record['inv_number'] = 'A50/000005'
    db.rollback()
    assert _blocks(db, 2050) == [(1, 3, True, k(2050, 7, 1), k(2050, 7, 3))]


def test_moving_a_record_to_another_year_releases_its_number_in_the_old_period(db, switch):
    records = [_insert(db, d(2051, 1, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with invoice.recordToUpdate(records[1]['id']) as record:
        record['date'] = d(2052, 1, 5)
        record['inv_number'] = None
    db.commit()
    assert _blocks(db, 2051) == [(1, 1, True, k(2051, 1, 1), k(2051, 1, 1)),
                                 (2, 2, False, k(2051, 1, 1), k(2051, 1, 3)),
                                 (3, 3, True, k(2051, 1, 3), k(2051, 1, 3))]
    assert invoice.record(records[1]['id'], mode='record')['inv_number'] == 'A52/000001'


def test_recycle_without_order_field_is_a_configuration_error(db, switch):
    switch()
    with pytest.raises(GnrSqlBusinessLogicException):
        _insert(db, d(2053, 1, 1))
    db.rollback()


def test_without_order_field_and_recycle_no_order_is_checked(db, switch):
    switch(recycle=False)
    _insert(db, d(2054, 6, 1))
    assert _insert(db, d(2054, 1, 1))['inv_number'] == 'A54/000002'


def test_order_by_insert_timestamp_never_recycles_into_the_past(db, switch):
    switch(order_field='__ins_ts')
    records = [_insert(db, d(2055, 1, n)) for n in (1, 2, 3)]
    _delete(db, records[1])
    assert _insert(db, d(2055, 1, 2))['inv_number'] == 'A55/000004'
    blocks = _blocks(db, 2055)
    assert [b[:3] for b in blocks] == [(1, 1, True), (2, 2, False), (3, 4, True)]
    assert blocks[1][3] <= blocks[1][4] <= blocks[2][4]


def test_guess_gives_the_number_the_insert_will_take(db, switch):
    records = [_insert(db, d(2056, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    invoice = db.table('invc.invoice')
    sequence, info = invoice.sysCounter('inv_number').guessNextSequence(
        tblobj=invoice, field='inv_number', record=dict(date=d(2056, 1, 11)))
    assert (sequence, info['recycled']) == ('A56/000002', True)
    assert _insert(db, d(2056, 1, 11))['inv_number'] == sequence


def test_guess_on_a_new_record_ordered_by_insert_timestamp(db, switch):
    """#1888 review, point 3: a record not inserted yet has no __ins_ts"""
    switch(order_field='__ins_ts')
    records = [_insert(db, d(2057, 1, n)) for n in (1, 2)]
    _delete(db, records[0])
    invoice = db.table('invc.invoice')
    sequence, info = invoice.sysCounter('inv_number').guessNextSequence(
        tblobj=invoice, field='inv_number', record=dict(date=d(2057, 1, 3)))
    assert (sequence, info['recycled']) == ('A57/000003', False)
    newrecord = invoice.newrecord(date=d(2057, 1, 3))
    invoice._sequencesOnLoading(newrecord, recInfo={})
    assert newrecord['inv_number'] == 'A57/000003'


def test_switch_on_continues_a_period_numbered_by_adm_counter(db, monkeypatch):
    """#1888 review, point 1: the period is loaded from the table under the lock"""
    records = [_insert(db, d(2058, 1, n)) for n in (1, 2, 3, 4)]
    _delete(db, records[1])
    previous = _set_switch(db, COUNTER)
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
    try:
        assert _insert(db, d(2058, 1, 10))['inv_number'] == 'A58/000005'
        assert _insert(db, d(2058, 1, 2))['inv_number'] == 'A58/000002'
        assert _blocks(db, 2058) == [(1, 5, True, k(2058, 1, 1), k(2058, 1, 10))]
    finally:
        db.application.config.setItem('experimental', previous.value if previous else Bag())
        db.rollback()


def test_a_neighbour_removed_outside_the_triggers_does_not_block_a_delete(db, switch):
    """#1888 review, point 4"""
    records = [_insert(db, d(2059, 1, n)) for n in (1, 2, 3, 4, 5)]
    invoice = db.table('invc.invoice')
    invoice.sql_deleteSelection(where='$id=:pk', pk=records[1]['id'])
    db.commit()
    _delete(db, records[2])
    blocks = _blocks(db, 2059)
    assert [b[:3] for b in blocks] == [(1, 2, True), (3, 3, False), (4, 5, True)]
    assert blocks[0][4] is None
    assert db.table('sys.counter').checkCounter(table='invc.invoice', field='inv_number')


def test_star_leaves_a_recycling_counter_without_order_field_on_adm_counter(db, monkeypatch):
    """#1888 review, point 2"""
    previous = _set_switch(db, '*')
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(), raising=False)
    try:
        assert invoice.sysCounter('inv_number', dict(date=d(2060, 1, 1))) is None
        assert _insert(db, d(2060, 1, 1))['inv_number'] == 'A60/000001'
        assert _blocks(db, 2060) == []
        monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
        assert invoice.sysCounter('inv_number', dict(date=d(2061, 1, 1))) is not None
    finally:
        db.application.config.setItem('experimental', previous.value if previous else Bag())
        db.rollback()


def test_switch_off_keeps_adm_counter(db):
    assert _insert(db, d(2062, 1, 1))['inv_number'] == 'A62/000001'
    assert _blocks(db, 2062) == []


def test_analyze_load_and_check_a_counter_numbered_by_adm_counter(db, monkeypatch):
    records = [_insert(db, d(2063, 1, n)) for n in (1, 2, 3, 4)]
    _delete(db, records[1])
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
    sys_counter = db.table('sys.counter')
    report = sys_counter.analyzeCounter(table='invc.invoice', field='inv_number')
    label = [key for key in report if key.endswith('/2063')]
    assert len(label) == 1
    assert report[label[0]] == dict(count=3, errors=[])
    assert sys_counter.loadCounter(table='invc.invoice', field='inv_number')[label[0]] == 'loaded'
    db.commit()
    assert _blocks(db, 2063) == [(1, 1, True, k(2063, 1, 1), k(2063, 1, 1)),
                                 (2, 2, False, k(2063, 1, 1), k(2063, 1, 3)),
                                 (3, 4, True, k(2063, 1, 3), k(2063, 1, 4))]
    assert label[0] not in sys_counter.checkCounter(table='invc.invoice', field='inv_number')


def test_analyze_reports_numbers_out_of_order(db, monkeypatch):
    _insert(db, d(2064, 3, 1))
    db.table('invc.invoice').insert(dict(date=d(2064, 2, 1), inv_number='A64/000002'))
    db.commit()
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
    sys_counter = db.table('sys.counter')
    report = sys_counter.analyzeCounter(table='invc.invoice', field='inv_number')
    errors = [v['errors'] for key, v in report.items() if key.endswith('/2064')][0]
    assert [e['kind'] for e in errors] == ['wrong_order']
    loaded = sys_counter.loadCounter(table='invc.invoice', field='inv_number')
    assert [v for key, v in loaded.items() if key.endswith('/2064')][0] != 'loaded'
