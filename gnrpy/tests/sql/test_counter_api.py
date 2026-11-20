"""The counter API of gnrdbo (TableBase.*CounterColumn) on adm.counter and on
sys.counter, and adm.counter claiming a number set by hand (#1908).

Every test runs on both counters: 'adm' leaves the experimental switch off,
'sys' turns it on for ``invc.invoice.inv_number`` with an order_field. Each test
gives the counter a code of its own, and each counter numbers its own year (adm
2093, sys 2094), so every run writes its own series. Runs on SQLite and PostgreSQL.
"""

import datetime

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException

from core.common import BaseGnrTest

COUNTER = 'invc.invoice.inv_number'
YEARS = dict(adm=2093, sys=2094)


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(params=['db_sqlite', 'db_pg'])
def db(request):
    return request.getfixturevalue(request.param)


def _set_switch(db, value):
    config = db.application.config
    experimental = config['experimental']
    if not isinstance(experimental, Bag):
        experimental = Bag()
        config.setItem('experimental', experimental)
    if value is None:
        experimental.pop('new_counters')
    else:
        experimental.setItem('new_counters', None, counters=value)


class _Counter(object):
    def __init__(self, db, kind, monkeypatch):
        self.db = db
        self.kind = kind
        self.monkeypatch = monkeypatch
        self.invoice = db.table('invc.invoice')
        self.year = YEARS[kind]
        self.code = None

    def series(self, tag):
        "The counter numbers the series of code tag from now on"
        self.code = tag
        pars = dict(format='$K$YY/$NNNNNN', code=self.code, period='YY', date_field='date', recycle=True)
        if self.kind == 'sys':
            pars['order_field'] = 'date'

        def counter_inv_number(record=None):
            return dict(pars)
        self.monkeypatch.setattr(self.invoice, 'counter_inv_number', counter_inv_number, raising=False)
        return self

    def sequence(self, number):
        return '%s%s/%06i' % (self.code, str(self.year)[2:], number)

    def number(self, record):
        return int(record['inv_number'][-6:])

    def insert(self, day, **kwargs):
        record = dict(date=self.d(day), **kwargs)
        self.invoice.insert(record)
        self.db.commit()
        return record

    def delete(self, record):
        self.invoice.delete(self.invoice.record(record['id'], mode='record'))
        self.db.commit()

    def raw_delete(self, record):
        "a record removed outside the triggers: its number is neither released nor in use"
        self.invoice.raw_delete(self.invoice.record(record['id'], mode='record'))
        self.db.commit()

    def anchor(self, day=1):
        "a record of the series, for the calls that name the series by a record"
        return dict(date=self.d(day))

    def d(self, day):
        "day of the year of the counter: the test series keep their dates in order"
        return datetime.date(self.year, 1, 1) + datetime.timedelta(days=day - 1)


@pytest.fixture(params=['adm', 'sys'])
def counter(request, db, monkeypatch):
    if request.param == 'sys':
        _set_switch(db, COUNTER)
    yield _Counter(db, request.param, monkeypatch)
    _set_switch(db, None)
    db.rollback()


def test_a_free_number_set_by_hand_is_claimed_and_not_given_again(counter):
    c = counter.series('A')
    records = [c.insert(day) for day in (10, 11, 12)]
    c.delete(records[1])
    assert c.invoice.freeCounterSequences('inv_number', c.anchor())[0]['number'] == 2
    c.insert(11, inv_number=c.sequence(2))
    assert c.invoice.freeCounterSequences('inv_number', c.anchor()) == []
    assert c.number(c.insert(13)) == 4


def test_a_record_deleted_and_written_again_keeps_the_counter_on_it(counter):
    """erpy-engine#118: the last record of the series deleted and written again with
    its own number; the next record must not get that number"""
    c = counter.series('B')
    records = [c.insert(day) for day in (1, 2)]
    c.delete(records[1])
    c.insert(2, inv_number=c.sequence(2))
    assert c.number(c.insert(3)) == 3


def test_a_number_above_the_last_one_frees_the_numbers_between(counter):
    c = counter.series('C')
    c.insert(1)
    c.insert(5, inv_number=c.sequence(4))
    free = c.invoice.freeCounterSequences('inv_number', c.anchor())
    assert [(f['number'], f['date_from'], f['date_to']) for f in free] == [(2, c.d(1), c.d(5)), (3, c.d(1), c.d(5))]
    assert c.invoice.lastCounterSequence('inv_number', c.anchor()) == dict(number=4, date=c.d(5))
    assert c.number(c.insert(3)) == 2
    assert c.number(c.insert(6)) == 5


def test_a_number_held_by_another_record_is_refused(counter):
    c = counter.series('D')
    c.insert(1)
    with pytest.raises(GnrSqlBusinessLogicException):
        c.insert(2, inv_number=c.sequence(1))
    c.db.rollback()


def test_a_first_claim_that_finds_the_counter_row_inserted_meanwhile_goes_on(counter):
    """#1909 review: two first claims of a series together; the second finds the
    row of the counter inserted by the first after its own check"""
    c = counter.series('O')
    c.insert(1, inv_number=c.sequence(1))
    counter_tbl = c.db.table('%s.counter' % c.kind)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(counter_tbl, 'existsRecord', lambda *args, **kwargs: False)
        assert c.number(c.insert(2, inv_number=c.sequence(2))) == 2
    assert c.number(c.insert(3)) == 3


def test_a_number_set_by_hand_before_the_last_date_is_refused(counter):
    c = counter.series('E')
    c.insert(10)
    with pytest.raises(GnrSqlBusinessLogicException):
        c.insert(5, inv_number=c.sequence(2))
    c.db.rollback()


def test_a_draft_that_gives_up_its_number_gives_it_back(counter):
    c = counter.series('F')
    c.insert(1)
    draft = c.insert(2, inv_number=c.sequence(2), __is_draft=True)
    with c.invoice.recordToUpdate(draft['id']) as record:
        record['inv_number'] = None
    c.db.commit()
    assert c.number(c.insert(3)) == 2


def test_realign_rebuilds_the_series_from_the_table(counter):
    c = counter.series('G')
    records = [c.insert(day) for day in (1, 2, 3)]
    c.raw_delete(records[1])
    c.raw_delete(records[2])
    c.invoice.realignCounterColumn('inv_number', c.anchor())
    c.db.commit()
    assert c.invoice.lastCounterSequence('inv_number', c.anchor()) == dict(number=1, date=c.d(1))
    assert c.number(c.insert(4)) == 2


def test_realign_with_a_floor_keeps_the_numbers_in_use_elsewhere(counter):
    c = counter.series('H')
    c.insert(1)
    c.invoice.realignCounterColumn('inv_number', c.anchor(), floor=10)
    c.db.commit()
    assert c.invoice.lastCounterSequence('inv_number', c.anchor())['number'] == 10
    assert c.number(c.insert(2)) == 11


def test_realign_frees_a_number_removed_outside_the_triggers(counter):
    c = counter.series('I')
    records = [c.insert(day) for day in (1, 2, 3)]
    c.raw_delete(records[1])
    c.invoice.realignCounterColumn('inv_number', c.anchor())
    c.db.commit()
    assert [f['number'] for f in c.invoice.freeCounterSequences('inv_number', c.anchor())] == [2]
    assert c.number(c.insert(2, inv_number=c.sequence(2))) == 2


def test_format_of_a_number_of_the_series(counter):
    c = counter.series('J')
    assert c.invoice.formatCounterSequence('inv_number', c.anchor(), 7) == c.sequence(7)


def test_last_number_of_an_empty_series(counter):
    c = counter.series('K')
    assert c.invoice.lastCounterSequence('inv_number', c.anchor()) == dict(number=0, date=None)
    assert c.invoice.freeCounterSequences('inv_number', c.anchor()) == []


def test_adm_takes_a_lost_number_below_the_counter(counter):
    """#1904: a number below the counter and in no hole is not necessarily in use;
    adm.counter asks the table. sys.counter keeps it occupied until a realign"""
    if counter.kind != 'adm':
        pytest.skip('sys.counter keeps a number removed outside the triggers occupied')
    c = counter.series('L')
    records = [c.insert(day) for day in (1, 2, 3)]
    c.raw_delete(records[1])
    assert c.number(c.insert(2, inv_number=c.sequence(2))) == 2
    assert c.number(c.insert(4)) == 4


def test_a_number_assigned_twice_in_one_save_is_taken(counter):
    """The cause of #1904: an application assigns the counters in its trigger, then
    the save assigns them again. Both counters find the number held by no other
    record and take it (erpy-engine#126)"""
    c = counter.series('M')
    record = dict(date=c.d(1))
    c.invoice.assignCounterColumn(field='inv_number', record=record)
    c.invoice.insert(record)
    c.db.commit()
    assert c.number(record) == 1
    assert c.number(c.insert(2)) == 2


def test_realign_every_series_of_the_field(counter):
    c = counter.series('N')
    records = [c.insert(day) for day in (1, 2)]
    c.raw_delete(records[1])
    c.invoice.realignCounterColumn('inv_number')
    c.db.commit()
    assert c.number(c.insert(3)) == 2


def test_realign_of_a_switched_off_counter_does_nothing(counter):
    c = counter.series('P')
    c.insert(1)
    c.monkeypatch.setattr(c.invoice, 'counter_inv_number', lambda record=None: False, raising=False)
    c.invoice.realignCounterColumn('inv_number')
    if c.kind == 'adm':
        c.db.table('adm.counter').initializeTableSequences(c.invoice)
