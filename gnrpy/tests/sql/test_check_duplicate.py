"""Tests for Table.checkDuplicate vs logically deleted (archived) records.

Covers issue #896: ``db migrate -u`` aborted with a UniqueViolation when a
userobject installed from package resources had been archived (logically
deleted): the duplicate check performed before inserting did not see
logically deleted rows, so the insert collided with the unique index on
``identifier``.

Uses the SQLite instance of the test_invoice project.
"""

import datetime

import pytest

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _archive(tbl, pkey):
    """Logically delete a record by setting its __del_ts."""
    row = tbl.query(where='$%s=:pk' % tbl.pkey, pk=pkey,
                    for_update=True).fetch()[0]
    old_record = dict(row)
    old_record.pop('pkey', None)
    record = dict(old_record)
    record['__del_ts'] = datetime.datetime.now()
    tbl.update(record, old_record=old_record)
    tbl.db.commit()


class TestCheckDuplicateLogicalDeleted:

    def test_default_excludes_archived(self, db_sqlite):
        tbl = db_sqlite.table('invc.customer')
        record = tbl.insert(dict(account_name='Archived Duplicate Test'))
        db_sqlite.commit()
        assert tbl.checkDuplicate(account_name='Archived Duplicate Test')
        _archive(tbl, record['id'])
        assert not tbl.checkDuplicate(account_name='Archived Duplicate Test')

    def test_exclude_logical_deleted_false_sees_archived(self, db_sqlite):
        tbl = db_sqlite.table('invc.customer')
        record = tbl.insert(dict(account_name='Archived Duplicate Test 2'))
        db_sqlite.commit()
        _archive(tbl, record['id'])
        assert tbl.checkDuplicate(account_name='Archived Duplicate Test 2',
                                  excludeLogicalDeleted=False)

    def test_unarchived_record_still_duplicate(self, db_sqlite):
        tbl = db_sqlite.table('invc.customer')
        tbl.insert(dict(account_name='Live Duplicate Test'))
        db_sqlite.commit()
        assert tbl.checkDuplicate(account_name='Live Duplicate Test',
                                  excludeLogicalDeleted=False)


class TestUserobjectArchivedDuplicate:
    """Replicates the migrate -u scenario of issue #896 on adm.userobject.

    Runs on PostgreSQL because adm.userobject formula columns use
    postgres-only functions.
    """

    USEROBJECT = dict(code='test_uo_896', pkg='invc',
                      tbl='invc.customer', objtype='template')

    @pytest.fixture(autouse=True)
    def _purge_userobject(self, db_pg):
        """Hard-delete the test userobject before and after each test.

        The db_pg fixture may run against a persistent PostgreSQL
        database, so the archived row would otherwise survive between
        runs and collide with the insert through the very unique index
        this test is about.
        """
        self._hard_delete(db_pg)
        yield
        self._hard_delete(db_pg)

    def _hard_delete(self, db):
        tbl = db.table('adm.userobject')
        rows = tbl.query(where='$code = :c', c=self.USEROBJECT['code'],
                         excludeLogicalDeleted=False,
                         for_update=True).fetch()
        for row in rows:
            tbl.delete(dict(row))
        db.commit()

    def test_archived_userobject_detected(self, db_pg):
        tbl = db_pg.table('adm.userobject')
        record = tbl.insert(dict(data=None, private=False, userid=None,
                                 **self.USEROBJECT))
        db_pg.commit()
        assert tbl.checkDuplicate(**self.USEROBJECT)
        _archive(tbl, record['id'])
        # the default check no longer sees the row (this is what caused
        # the UniqueViolation on migrate), while passing
        # excludeLogicalDeleted=False — as checkResourceUserObject now
        # does — still detects it and prevents the insert
        assert not tbl.checkDuplicate(**self.USEROBJECT)
        assert tbl.checkDuplicate(excludeLogicalDeleted=False,
                                  **self.USEROBJECT)
