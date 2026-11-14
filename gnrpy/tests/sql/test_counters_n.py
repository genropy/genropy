"""Tests for adm.counters_n: the numbers of a counter series kept as blocks.

The counter is ``invc.invoice.inv_number`` of the test_invoice project
(format ``$K$YY/$NNNNNN``, code ``A``, ``date_field='date'``,
``recycle=True``). The tests enable the experimental switch
``new_counters/counters`` in the application config and give the counter an
``order_field``, which the new model requires to recycle. Each test works on
its own year, so on its own series. Runs on SQLite and PostgreSQL.
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


@pytest.fixture
def switch(db, monkeypatch):
    """Enables the new model for the invoice counter; returns a setter for its pars"""
    config = db.application.config
    previous = config.getNode('experimental')
    experimental = Bag(previous.value) if previous and isinstance(previous.value, Bag) else Bag()
    experimental.setItem('new_counters', None, counters=COUNTER)
    config.setItem('experimental', experimental)
    invoice = db.table('invc.invoice')

    def set_pars(**extra):
        monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(**extra), raising=False)

    set_pars(order_field='date')
    yield set_pars
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
    codekey = db.table('adm.counter').query(columns='$codekey', where='$tbl=:t AND $period=:p',
                                            t='invoice', p=str(year), addPkeyColumn=False).fetch()
    assert len(codekey) == 1
    rows = db.table('adm.counters_n').query(
        columns='$block_start,$block_end,$occupied,$order_first,$order_last',
        where='$counter_codekey=:c', c=codekey[0]['codekey'], order_by='$block_start',
        addPkeyColumn=False).fetch()
    return [(r['block_start'], r['block_end'], bool(r['occupied']), r['order_first'], r['order_last'])
            for r in rows]


def _counter(db, year):
    return db.table('adm.counter').query(columns='$counter', where='$tbl=:t AND $period=:p',
                                         t='invoice', p=str(year), addPkeyColumn=False).fetch()[0]['counter']


def _delete(db, record):
    invoice = db.table('invc.invoice')
    invoice.delete(invoice.record(record['id'], mode='record'))
    db.commit()


def d(year, month, day):
    return datetime.date(year, month, day)


def test_new_numbers_make_one_occupied_block(db, switch):
    records = [_insert(db, d(2041, 1, n)) for n in (10, 11, 12)]
    assert [r['inv_number'] for r in records] == ['A41/000001', 'A41/000002', 'A41/000003']
    assert _blocks(db, 2041) == [(1, 3, True, '2041-01-10', '2041-01-12')]
    assert _counter(db, 2041) == 3


def test_release_in_the_middle_leaves_a_free_block_with_its_window(db, switch):
    records = [_insert(db, d(2042, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    assert _blocks(db, 2042) == [(1, 1, True, '2042-01-10', '2042-01-10'),
                                 (2, 2, False, '2042-01-10', '2042-01-12'),
                                 (3, 3, True, '2042-01-12', '2042-01-12')]


def test_a_free_number_is_recycled_only_inside_its_window(db, switch):
    records = [_insert(db, d(2043, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    outside = _insert(db, d(2043, 1, 20))
    assert outside['inv_number'] == 'A43/000004'
    inside = _insert(db, d(2043, 1, 11))
    assert inside['inv_number'] == 'A43/000002'
    assert _blocks(db, 2043) == [(1, 4, True, '2043-01-10', '2043-01-20')]


def test_release_inside_a_long_block_reads_the_new_edges(db, switch):
    records = [_insert(db, d(2044, 2, n)) for n in (1, 2, 3, 4, 5)]
    _delete(db, records[2])
    assert _blocks(db, 2044) == [(1, 2, True, '2044-02-01', '2044-02-02'),
                                 (3, 3, False, '2044-02-02', '2044-02-04'),
                                 (4, 5, True, '2044-02-04', '2044-02-05')]


def test_release_of_the_last_number_takes_the_series_back(db, switch):
    records = [_insert(db, d(2045, 3, n)) for n in (1, 2, 3)]
    _delete(db, records[1])
    _delete(db, records[2])
    assert _blocks(db, 2045) == [(1, 1, True, '2045-03-01', '2045-03-01')]
    assert _counter(db, 2045) == 1
    assert _insert(db, d(2045, 3, 9))['inv_number'] == 'A45/000002'


def test_a_number_set_by_hand_beyond_the_last_leaves_the_numbers_between_free(db, switch):
    _insert(db, d(2046, 4, 1))
    _insert(db, d(2046, 4, 5), inv_number='A46/000004')
    assert _blocks(db, 2046) == [(1, 1, True, '2046-04-01', '2046-04-01'),
                                 (2, 3, False, '2046-04-01', '2046-04-05'),
                                 (4, 4, True, '2046-04-05', '2046-04-05')]
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
    assert _blocks(db, 2048) == [(1, 1, True, '2048-06-01', '2048-06-01')]


def test_changing_the_number_releases_the_old_one(db, switch):
    records = [_insert(db, d(2049, 7, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with invoice.recordToUpdate(records[2]['id']) as record:
        record['inv_number'] = 'A49/000005'
    db.commit()
    assert _blocks(db, 2049) == [(1, 2, True, '2049-07-01', '2049-07-02'),
                                 (3, 4, False, '2049-07-02', '2049-07-03'),
                                 (5, 5, True, '2049-07-03', '2049-07-03')]


def test_a_number_moved_after_a_later_date_is_refused(db, switch):
    records = [_insert(db, d(2056, 7, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with pytest.raises(GnrSqlBusinessLogicException):
        with invoice.recordToUpdate(records[1]['id']) as record:
            record['inv_number'] = 'A56/000005'
    db.rollback()
    assert _blocks(db, 2056) == [(1, 3, True, '2056-07-01', '2056-07-03')]


def test_recycle_without_order_field_is_a_configuration_error(db, switch):
    switch()
    with pytest.raises(GnrSqlBusinessLogicException):
        _insert(db, d(2050, 1, 1))
    db.rollback()


def test_without_order_field_and_recycle_no_order_is_checked(db, switch):
    switch(recycle=False)
    _insert(db, d(2051, 6, 1))
    assert _insert(db, d(2051, 1, 1))['inv_number'] == 'A51/000002'


def test_guess_gives_the_number_the_insert_will_take(db, switch):
    records = [_insert(db, d(2052, 1, n)) for n in (10, 11, 12)]
    _delete(db, records[1])
    invoice = db.table('invc.invoice')
    sequence, info = invoice.counterTable('inv_number').guessNextSequence(
        tblobj=invoice, field='inv_number', record=dict(date=d(2052, 1, 11)))
    assert (sequence, info['recycled']) == ('A52/000002', True)
    assert _insert(db, d(2052, 1, 11))['inv_number'] == sequence


def test_switch_off_keeps_adm_counter(db):
    record = _insert(db, d(2053, 1, 1))
    assert record['inv_number'] == 'A53/000001'
    assert db.table('adm.counters_n').query(where='$counter_codekey LIKE :c', c='%53%').count() == 0


def test_analyze_load_and_check_a_series_numbered_by_adm_counter(db, monkeypatch):
    records = [_insert(db, d(2054, 1, n)) for n in (1, 2, 3, 4)]
    _delete(db, records[1])
    counters_n = db.table('adm.counters_n')
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
    codekey = [k for k in counters_n.analyzeCounter(table='invc.invoice', field='inv_number') if k.endswith('54')]
    assert len(codekey) == 1
    report = counters_n.analyzeCounter(table='invc.invoice', field='inv_number')
    assert report[codekey[0]] == dict(count=3, errors=[])
    assert counters_n.loadCounter(table='invc.invoice', field='inv_number')[codekey[0]] == 'loaded'
    db.commit()
    assert _blocks(db, 2054) == [(1, 1, True, '2054-01-01', '2054-01-01'),
                                 (2, 2, False, '2054-01-01', '2054-01-03'),
                                 (3, 4, True, '2054-01-03', '2054-01-04')]
    assert codekey[0] not in counters_n.checkCounter(table='invc.invoice', field='inv_number')


def test_analyze_reports_numbers_out_of_order(db, monkeypatch):
    _insert(db, d(2055, 3, 1))
    db.table('invc.invoice').insert(dict(date=d(2055, 2, 1), inv_number='A55/000002'))
    db.commit()
    invoice = db.table('invc.invoice')
    monkeypatch.setattr(invoice, 'counter_inv_number', _counter_pars(order_field='date'), raising=False)
    counters_n = db.table('adm.counters_n')
    report = counters_n.analyzeCounter(table='invc.invoice', field='inv_number')
    errors = [v['errors'] for k, v in report.items() if k.endswith('55')][0]
    assert [e['kind'] for e in errors] == ['wrong_order']
    loaded = counters_n.loadCounter(table='invc.invoice', field='inv_number')
    assert [v for k, v in loaded.items() if k.endswith('55')][0] != 'loaded'


def test_order_by_insert_timestamp_never_recycles_into_the_past(db, switch):
    switch(order_field='__ins_ts')
    records = [_insert(db, d(2057, 1, n)) for n in (1, 2, 3)]
    _delete(db, records[1])
    assert _insert(db, d(2057, 1, 2))['inv_number'] == 'A57/000004'
    blocks = _blocks(db, 2057)
    assert [b[:3] for b in blocks] == [(1, 1, True), (2, 2, False), (3, 4, True)]
    assert blocks[1][3] < blocks[1][4] < blocks[2][4]


def test_moving_a_record_to_another_year_releases_its_number_in_the_old_series(db, switch):
    records = [_insert(db, d(2058, 1, n)) for n in (1, 2, 3)]
    invoice = db.table('invc.invoice')
    with invoice.recordToUpdate(records[1]['id']) as record:
        record['date'] = d(2059, 1, 5)
        record['inv_number'] = None
    db.commit()
    assert _blocks(db, 2058) == [(1, 1, True, '2058-01-01', '2058-01-01'),
                                 (2, 2, False, '2058-01-01', '2058-01-03'),
                                 (3, 3, True, '2058-01-03', '2058-01-03')]
    assert invoice.record(records[1]['id'], mode='record')['inv_number'] == 'A59/000001'
