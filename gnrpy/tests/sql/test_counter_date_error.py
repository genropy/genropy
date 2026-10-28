"""Tests for the localization of the adm.counter business logic errors.

Covers issue #1399: assigning a counter with a ``date_field`` and no
``date_tolerant`` to a record dated before the counter's ``last_used``
showed the user raw markers ('!!Incompatible date assigning [it]Protocollo
counter'), because the message was composed with the markers still in it
and the catalog entry carried broken placeholders. The message is now
translated when composed, in the locale of the current environment.

``invc.invoice.counter_inv_number`` has ``date_field='date'`` and no
``date_tolerant``. Uses the SQLite instance of the test_invoice project.
"""

import datetime

import pytest

from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _insert_invoice(db, date):
    db.table('invc.invoice').insert(dict(date=date))


def _assert_user_message(db, exc, locale, expected):
    assert exc.msgargs['msg'] == expected
    shown = db.localizer.translate(str(exc), language=locale)
    assert shown.endswith(': %s' % expected)
    assert '!!' not in shown
    assert '[' not in shown


@pytest.mark.parametrize('locale,year,expected', [
    ('it', 2031, "Data incompatibile per l'assegnazione del contatore Invoice number"),
    ('en', 2032, 'Incompatible date assigning Invoice number counter'),
])
def test_date_before_last_used(db_sqlite, locale, year, expected):
    with db_sqlite.tempEnv(locale=locale):
        _insert_invoice(db_sqlite, datetime.date(year, 6, 15))
        db_sqlite.commit()
        try:
            with pytest.raises(GnrSqlBusinessLogicException) as excinfo:
                _insert_invoice(db_sqlite, datetime.date(year, 3, 1))
        finally:
            db_sqlite.rollback()
    _assert_user_message(db_sqlite, excinfo.value, locale, expected)


@pytest.mark.parametrize('locale,expected', [
    ('it', 'Manca date. Obbligatorio per il contatore inv_number'),
    ('en', 'Missing date. Mandatory for counter inv_number'),
])
def test_missing_date(db_sqlite, locale, expected):
    with db_sqlite.tempEnv(locale=locale):
        try:
            with pytest.raises(GnrSqlBusinessLogicException) as excinfo:
                _insert_invoice(db_sqlite, None)
        finally:
            db_sqlite.rollback()
    _assert_user_message(db_sqlite, excinfo.value, locale, expected)
