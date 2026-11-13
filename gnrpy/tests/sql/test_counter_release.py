"""Tests for adm.counter releasing and recycling numbers.

``invc.invoice.counter_inv_number`` recycles (``recycle=True``) with
``date_field='date'`` and no ``date_tolerant``: deleting an invoice gives
its number back as a hole, dated so that the number can only go to an
invoice whose date keeps the series in date order.

Covers:
- a released number whose adjacent numbers are not in use (free or lost)
  was taken for the tail of the series and the counter went back below
  numbers in use, which were then handed out again;
- the hole dates came from the adjacent numbers only, so a missing
  neighbour narrowed or dropped them;
- reusing a hole of several numbers left its start date unchanged, so a
  later number could take an earlier date;
- a counter already left below numbers in use is put back on release;
- a number set by hand is claimed: a free one is taken out of its hole, one
  above the counter raises it (also on a series without counter), leaving the
  numbers between free;
- the free numbers of a series, and a record named in counter_keep keeping
  its number.

Each test uses its own year, so its own counter. SQLite instance of the
test_invoice project.
"""

import datetime

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _invoice(db, date):
    record = dict(date=date)
    db.table('invc.invoice').insert(record)
    db.commit()
    return record


def _number(record):
    return int(record['inv_number'][-6:])


def _delete(db, record):
    tbl = db.table('invc.invoice')
    tbl.delete(tbl.record(record['id']).output('dict'))
    db.commit()


def _counter_key(db, record):
    return db.table('adm.counter').getCounterPkey(tblobj=db.table('invc.invoice'),
                                                  field='inv_number', record=record)


def _counter(db, record):
    counter_record = db.table('adm.counter').record(_counter_key(db, record)).output('record')
    holes = counter_record['holes']
    if isinstance(holes, str):
        holes = Bag(holes)
    holes = holes.digest('#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to') if holes else []
    return counter_record['counter'], counter_record['last_used'], [tuple(h) for h in holes]


def _lose_holes(db, record, **kwargs):
    "the state left by a release that did not record the hole: the numbers are lost"
    with db.table('adm.counter').recordToUpdate(_counter_key(db, record), mode='record') as counter_record:
        counter_record['holes'] = None
        counter_record.update(kwargs)
    db.commit()


def _series(db, year, days):
    return [_invoice(db, datetime.date(year, 1, d)) for d in days]


def test_release_between_numbers_not_in_use_keeps_the_counter(db_sqlite):
    "the lost numbers next to the released one come back in its hole"
    d = lambda n: datetime.date(2041, 1, n)
    inv = _series(db_sqlite, 2041, range(1, 6))
    _delete(db_sqlite, inv[1])
    _delete(db_sqlite, inv[3])
    _lose_holes(db_sqlite, inv[0])
    _delete(db_sqlite, inv[2])
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(2, 4, d(1), d(5))])
    assert _number(_invoice(db_sqlite, d(6))) == 6
    assert _number(_invoice(db_sqlite, d(2))) == 2


def test_adjacent_holes_merge(db_sqlite):
    d = lambda n: datetime.date(2046, 1, n)
    inv = _series(db_sqlite, 2046, range(1, 7))
    _delete(db_sqlite, inv[1])
    assert _counter(db_sqlite, inv[0]) == (6, d(6), [(2, 2, d(1), d(3))])
    _delete(db_sqlite, inv[3])
    assert _counter(db_sqlite, inv[0]) == (6, d(6), [(2, 2, d(1), d(3)), (4, 4, d(3), d(5))])
    _delete(db_sqlite, inv[2])
    assert _counter(db_sqlite, inv[0]) == (6, d(6), [(2, 4, d(1), d(5))])


def test_release_with_nothing_in_use_below(db_sqlite):
    d = lambda n: datetime.date(2047, 1, n)
    inv = _series(db_sqlite, 2047, range(1, 4))
    _delete(db_sqlite, inv[0])
    assert _counter(db_sqlite, inv[1]) == (3, d(3), [(1, 1, None, d(2))])
    assert _number(_invoice(db_sqlite, d(1))) == 1


def test_release_of_the_tail_goes_back_to_the_highest_number_in_use(db_sqlite):
    d = lambda n: datetime.date(2042, 1, n)
    inv = _series(db_sqlite, 2042, range(1, 5))
    _delete(db_sqlite, inv[2])
    _lose_holes(db_sqlite, inv[0])
    _delete(db_sqlite, inv[3])
    assert _counter(db_sqlite, inv[0]) == (2, d(2), [])
    assert _number(_invoice(db_sqlite, d(3))) == 3


def test_release_of_the_last_number(db_sqlite):
    d = lambda n: datetime.date(2045, 1, n)
    inv = _series(db_sqlite, 2045, range(1, 4))
    _delete(db_sqlite, inv[2])
    assert _counter(db_sqlite, inv[0]) == (2, d(2), [])
    assert _number(_invoice(db_sqlite, d(3))) == 3


def test_reusing_a_hole_keeps_the_numbers_in_date_order(db_sqlite):
    d = lambda n: datetime.date(2043, 1, n)
    inv = _series(db_sqlite, 2043, range(1, 6))
    for record in inv[1:4]:
        _delete(db_sqlite, record)
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(2, 4, d(1), d(5))])
    assert _number(_invoice(db_sqlite, d(4))) == 2
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(3, 4, d(4), d(5))])
    try:
        with pytest.raises(GnrSqlBusinessLogicException):
            _invoice(db_sqlite, d(2))
    finally:
        db_sqlite.rollback()
    assert _number(_invoice(db_sqlite, d(4))) == 3


def test_a_counter_left_below_numbers_in_use_is_put_back(db_sqlite):
    d = lambda n: datetime.date(2044, 1, n)
    inv = _series(db_sqlite, 2044, range(1, 6))
    _lose_holes(db_sqlite, inv[0], counter=2, last_used=d(2))
    _delete(db_sqlite, inv[2])
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(3, 3, d(2), d(4))])
    assert _number(_invoice(db_sqlite, d(6))) == 6


def _invoice_with_number(db, date, number):
    "an invoice given a free number by hand, as a draft form may"
    record = dict(date=date, inv_number='A%02i/%06i' % (date.year % 100, number))
    db.table('invc.invoice').insert(record)
    db.commit()
    return record


def test_a_free_number_chosen_by_hand_is_taken_out_of_its_hole(db_sqlite):
    d = lambda n: datetime.date(2048, 1, n)
    inv = _series(db_sqlite, 2048, range(1, 6))
    for record in inv[1:4]:
        _delete(db_sqlite, record)
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(2, 4, d(1), d(5))])
    assert _number(_invoice_with_number(db_sqlite, d(3), 3)) == 3
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(2, 2, d(1), d(3)), (4, 4, d(3), d(5))])


def test_a_free_number_takes_only_a_date_of_its_hole(db_sqlite):
    d = lambda n: datetime.date(2049, 1, n)
    inv = _series(db_sqlite, 2049, range(1, 6))
    _delete(db_sqlite, inv[2])
    try:
        with pytest.raises(GnrSqlBusinessLogicException):
            _invoice_with_number(db_sqlite, d(5), 3)
    finally:
        db_sqlite.rollback()
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(3, 3, d(2), d(4))])


def test_the_free_numbers_of_a_series(db_sqlite):
    d = lambda n: datetime.date(2050, 1, n)
    inv = _series(db_sqlite, 2050, range(1, 7))
    _delete(db_sqlite, inv[1])
    _delete(db_sqlite, inv[3])
    _delete(db_sqlite, inv[4])
    free = db_sqlite.table('adm.counter').holeSequences(tblobj=db_sqlite.table('invc.invoice'),
                                                         field='inv_number', record=inv[0])
    assert [(f['sequence'], f['date_from'], f['date_to']) for f in free] == [
        ('A50/000002', d(1), d(3)), ('A50/000004', d(3), d(6)), ('A50/000005', d(3), d(6))]


def test_the_last_record_written_again_with_its_number_takes_the_counter_back_up(db_sqlite):
    "deleted and written again with the number it had (as a re-accounting does): no number is handed out twice"
    d = lambda n: datetime.date(2052, 1, n)
    inv = _series(db_sqlite, 2052, range(1, 4))
    _delete(db_sqlite, inv[2])
    assert _counter(db_sqlite, inv[0]) == (2, d(2), [])
    assert _number(_invoice_with_number(db_sqlite, d(3), 3)) == 3
    assert _counter(db_sqlite, inv[0]) == (3, d(3), [])
    assert _number(_invoice(db_sqlite, d(4))) == 4


def test_a_number_above_the_counter_leaves_the_numbers_between_free(db_sqlite):
    d = lambda n: datetime.date(2053, 1, n)
    inv = _series(db_sqlite, 2053, range(1, 3))
    assert _number(_invoice_with_number(db_sqlite, d(5), 5)) == 5
    assert _counter(db_sqlite, inv[0]) == (5, d(5), [(3, 4, d(2), d(5))])
    assert _number(_invoice(db_sqlite, d(3))) == 3


def test_a_number_above_the_counter_takes_no_date_before_the_last_used(db_sqlite):
    d = lambda n: datetime.date(2054, 1, n)
    inv = _series(db_sqlite, 2054, range(1, 4))
    try:
        with pytest.raises(GnrSqlBusinessLogicException):
            _invoice_with_number(db_sqlite, d(2), 5)
    finally:
        db_sqlite.rollback()
    assert _counter(db_sqlite, inv[0]) == (3, d(3), [])


def test_a_number_in_use_below_the_counter_is_left_alone(db_sqlite):
    d = lambda n: datetime.date(2055, 1, n)
    inv = _series(db_sqlite, 2055, range(1, 4))
    tbl = db_sqlite.table('invc.invoice')
    with tbl.recordToUpdate(inv[1]['id']) as record:
        record['date'] = d(2)
    db_sqlite.commit()
    assert _counter(db_sqlite, inv[0]) == (3, d(3), [])


def test_a_number_forced_on_a_series_without_counter_starts_it_leaving_the_numbers_before_free(db_sqlite):
    d = lambda n: datetime.date(2056, 1, n)
    record = _invoice_with_number(db_sqlite, d(10), 4)
    assert _number(record) == 4
    assert _counter(db_sqlite, record) == (4, d(10), [(1, 3, None, d(10))])
    assert _number(_invoice(db_sqlite, d(5))) == 1
    assert _number(_invoice(db_sqlite, d(11))) == 5


def test_a_record_named_in_counter_keep_keeps_its_number(db_sqlite):
    d = lambda n: datetime.date(2051, 1, n)
    inv = _series(db_sqlite, 2051, range(1, 4))
    with db_sqlite.tempEnv(counter_keep='invc.invoice:%s' % inv[1]['id']):
        _delete(db_sqlite, inv[1])
    assert _counter(db_sqlite, inv[0]) == (3, d(3), [])
