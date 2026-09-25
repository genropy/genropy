"""Test for the empty IN filter (bug #1385).

An ``IN`` condition left empty by the user reached the driver as ``None`` and
rendered as ``IN NULL``: a syntax error on PostgreSQL, an ``OperationalError``
on SQLite, and an HTTP 500 with a row in the instance error table either way.

The empty collection was already handled — ``adaptTupleListSet`` rewrites the
fragment to FALSE (TRUE when negated) — but ``op_in`` never normalised
``None`` into one.

These tests go through the real wherebag path (``sqlWhereFromBag``) on real
databases, because the defect lived in the SQL that reached the driver.
"""

import os
import shutil
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from core.common import BaseGnrTest
from .common import get_pg_config

MARKER = '__empty_in_filter_test__'


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
    dbname = pg_conf.pop('database', 'test_empty_in_filter')
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


def _insert_records(db):
    tbl = db.table('invc.customer')
    for name in ('EmptyIn Test A', 'EmptyIn Test B'):
        tbl.insert(dict(account_name=name, notes=MARKER))
    db.commit()


def _cleanup_records(db):
    tbl = db.table('invc.customer')
    rows = tbl.query(where='$notes = :marker', marker=MARKER,
                     excludeDraft=False, excludeLogicalDeleted=False).fetch()
    for r in rows:
        tbl.delete(r)
    db.commit()


def _fetch(db, value, negate=False):
    """Run a wherebag whose second condition is an IN on account_name."""
    tbl = db.table('invc.customer')
    wherebag = Bag()
    wherebag.setItem('c_1', MARKER, column='notes', op='equal')
    attributes = dict(column='account_name', op='in', jc='and')
    if negate:
        attributes['not'] = 'not'
    wherebag.setItem('c_2', value, **attributes)
    where, sqlargs = tbl.sqlWhereFromBag(wherebag)
    return tbl.query(where=where, excludeDraft=False,
                     excludeLogicalDeleted=False, **sqlargs).fetch()


class _EmptyInFilter:
    """An IN over nothing matches nothing; negated, it matches everything."""

    def test_empty_in_returns_no_row(self, db):
        _cleanup_records(db)
        _insert_records(db)
        try:
            assert _fetch(db, None) == []
        finally:
            _cleanup_records(db)

    def test_empty_not_in_returns_every_row(self, db):
        _cleanup_records(db)
        _insert_records(db)
        try:
            assert len(_fetch(db, None, negate=True)) == 2
        finally:
            _cleanup_records(db)

    def test_non_empty_in_still_filters(self, db):
        _cleanup_records(db)
        _insert_records(db)
        try:
            rows = _fetch(db, 'EmptyIn Test A')
            assert [r['account_name'] for r in rows] == ['EmptyIn Test A']
        finally:
            _cleanup_records(db)


class TestEmptyInFilterSqlite(_EmptyInFilter):

    @pytest.fixture
    def db(self, db_sqlite):
        return db_sqlite


class TestEmptyInFilterPg(_EmptyInFilter):

    @pytest.fixture
    def db(self, db_pg):
        return db_pg
