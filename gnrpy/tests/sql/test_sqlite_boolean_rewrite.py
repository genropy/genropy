"""Test for SQLite boolean rewrite (bug #549).

The excludeDraft filter generates ``$__is_draft IS NOT TRUE``.
On PostgreSQL this correctly includes rows where __is_draft is NULL
(three-valued logic).  The old SQLite rewrite turned IS NOT TRUE
into ``!=1``, which loses NULL rows because ``NULL != 1`` is NULL.

These tests use the real model (customer with draftField=True) and
run actual queries through the adapter on both PG and SQLite to
verify the fix end-to-end.
"""

import os
import tempfile
import shutil
import pytest

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest
from .common import get_pg_config

DRAFT_MARKER = '__bool_rewrite_test__'


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
    dbname = pg_conf.pop('database', 'test_bool_rewrite')
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


def _insert_draft_records(db):
    """Insert 3 customer records with __is_draft NULL, FALSE, TRUE.

    Uses DRAFT_MARKER in notes so they can be found and cleaned up.
    Returns list of inserted pkeys.
    """
    tbl = db.table('invc.customer')
    pkeys = []
    for i, draft_val in enumerate([None, False, True]):
        record = tbl.insert(dict(
            account_name='BoolRewrite Test %i' % i,
            notes=DRAFT_MARKER,
            __is_draft=draft_val,
        ))
        pkeys.append(record['id'])
    db.commit()
    return pkeys


def _cleanup_draft_records(db):
    """Remove all records tagged with DRAFT_MARKER."""
    tbl = db.table('invc.customer')
    rows = tbl.query(
        where='$notes = :marker',
        marker=DRAFT_MARKER,
        excludeDraft=False,
        excludeLogicalDeleted=False
    ).fetch()
    for r in rows:
        tbl.delete(r)
    db.commit()


class TestExcludeDraftSqlite:
    """excludeDraft must include NULL and FALSE, exclude TRUE on SQLite."""

    def test_exclude_draft_includes_null_and_false(self, db_sqlite):
        _cleanup_draft_records(db_sqlite)
        pkeys = _insert_draft_records(db_sqlite)
        try:
            tbl = db_sqlite.table('invc.customer')
            rows = tbl.query(
                where='$notes = :marker',
                marker=DRAFT_MARKER,
                excludeDraft=True,
                excludeLogicalDeleted=False
            ).fetch()
            found = {r['pkey'] for r in rows}
            assert pkeys[0] in found, '__is_draft=NULL must be included'
            assert pkeys[1] in found, '__is_draft=FALSE must be included'
            assert pkeys[2] not in found, '__is_draft=TRUE must be excluded'
        finally:
            _cleanup_draft_records(db_sqlite)

    def test_exclude_draft_count(self, db_sqlite):
        _cleanup_draft_records(db_sqlite)
        _insert_draft_records(db_sqlite)
        try:
            tbl = db_sqlite.table('invc.customer')
            total = tbl.query(
                where='$notes = :marker',
                marker=DRAFT_MARKER,
                excludeDraft=False,
                excludeLogicalDeleted=False
            ).count()
            filtered = tbl.query(
                where='$notes = :marker',
                marker=DRAFT_MARKER,
                excludeDraft=True,
                excludeLogicalDeleted=False
            ).count()
            assert total == 3
            assert filtered == 2
        finally:
            _cleanup_draft_records(db_sqlite)


class TestExcludeDraftPgVsSqlite:
    """Same query on PG and SQLite must return the same results."""

    def test_draft_filter_same_count(self, db_pg, db_sqlite):
        for db in (db_pg, db_sqlite):
            _cleanup_draft_records(db)
            _insert_draft_records(db)
        try:
            counts = {}
            for name, db in [('pg', db_pg), ('sqlite', db_sqlite)]:
                tbl = db.table('invc.customer')
                counts[name] = tbl.query(
                    where='$notes = :marker',
                    marker=DRAFT_MARKER,
                    excludeDraft=True,
                    excludeLogicalDeleted=False
                ).count()
            assert counts['pg'] == counts['sqlite'] == 2
        finally:
            for db in (db_pg, db_sqlite):
                _cleanup_draft_records(db)

    def test_draft_filter_same_pkeys_excluded(self, db_pg, db_sqlite):
        for db in (db_pg, db_sqlite):
            _cleanup_draft_records(db)
        pkeys = {}
        for name, db in [('pg', db_pg), ('sqlite', db_sqlite)]:
            pkeys[name] = _insert_draft_records(db)
        try:
            for name, db in [('pg', db_pg), ('sqlite', db_sqlite)]:
                tbl = db.table('invc.customer')
                rows = tbl.query(
                    where='$notes = :marker',
                    marker=DRAFT_MARKER,
                    excludeDraft=True,
                    excludeLogicalDeleted=False
                ).fetch()
                found = {r['pkey'] for r in rows}
                assert len(found) == 2, '%s: expected 2 non-draft rows' % name
                assert pkeys[name][2] not in found, (
                    '%s: draft=TRUE must be excluded' % name
                )
        finally:
            for db in (db_pg, db_sqlite):
                _cleanup_draft_records(db)
