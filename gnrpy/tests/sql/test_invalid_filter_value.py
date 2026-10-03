"""Test for a filter value that does not convert to the column dtype (bug #1384).

Text typed into a filter on a numeric column made the where translator raise
the raw ``ValueError`` / ``decimal.InvalidOperation`` of the dtype parser: an
HTTP 500 with a row in the instance error table instead of a message naming
the column and the value.

These tests go through the real wherebag path (``sqlWhereFromBag``) on real
databases.
"""

import os
import shutil
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqltable import GnrSqlInvalidFilterValueException
from core.common import BaseGnrTest
from .common import get_pg_config


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope="module", autouse=True)
def sqlite_temp_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='module')
def db_sqlite(sqlite_temp_dir):
    app = GnrApp('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(sqlite_temp_dir, 'testing'),
    ))
    app.db.model.check(applyChanges=True)
    return app.db


@pytest.fixture(scope='module')
def db_pg():
    pg_conf, pg_instance = get_pg_config()
    dbname = pg_conf.pop('database', 'test_invalid_filter_value')
    try:
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='postgres',
            dbname=dbname,
            **pg_conf,
        ))
        app.db.model.check(applyChanges=True)
        yield app.db
    except Exception:
        pytest.skip('PostgreSQL not available')
    finally:
        if pg_instance is not None:
            pg_instance.stop()


def _where(db, table, column, value, op='equal'):
    wherebag = Bag()
    wherebag.setItem('c_1', value, column=column, op=op)
    return db.table(table).sqlWhereFromBag(wherebag)


class _InvalidFilterValue:

    def test_text_on_integer_column(self, db):
        with pytest.raises(GnrSqlInvalidFilterValueException) as excinfo:
            _where(db, 'invc.invoice_row', 'quantity', 'direct deposit')
        message = str(excinfo.value)
        assert 'direct deposit' in message
        assert 'Quantity' in message

    def test_text_in_list_on_integer_column(self, db):
        with pytest.raises(GnrSqlInvalidFilterValueException) as excinfo:
            _where(db, 'invc.invoice_row', 'quantity', '1,abc', op='in')
        assert '1,abc' in str(excinfo.value)

    def test_percent_in_value_renders(self, db):
        with pytest.raises(GnrSqlInvalidFilterValueException) as excinfo:
            _where(db, 'invc.invoice_row', 'quantity', '50% off')
        assert '50% off' in str(excinfo.value)

    def test_text_on_decimal_column(self, db):
        with pytest.raises(GnrSqlInvalidFilterValueException) as excinfo:
            _where(db, 'invc.discount_tier', 'min_amount', 'abc')
        message = str(excinfo.value)
        assert 'abc' in message
        assert 'Min Amount' in message

    def test_valid_value_still_converts(self, db):
        where, sqlargs = _where(db, 'invc.invoice_row', 'quantity', '3')
        assert sqlargs == {'quantity': 3}


class TestInvalidFilterValueSqlite(_InvalidFilterValue):

    @pytest.fixture
    def db(self, db_sqlite):
        return db_sqlite


class TestInvalidFilterValuePg(_InvalidFilterValue):

    @pytest.fixture
    def db(self, db_pg):
        return db_pg
