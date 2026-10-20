"""Data retention overrides and the cleanup action (#1555).

Uses the shared test_invoice fixture (``db_sqlite``), whose instance
includes ``gnrcore:sys``: ``sys.error`` carries a 60 days policy on ``__ins_ts``.
"""

import importlib.util
import os
from datetime import datetime, timedelta

from core.common import BaseGnrTest

CLEANUP_ACTION = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'projects', 'gnrcore',
                              'packages', 'sys', 'resources', 'tables', 'dataretention',
                              'action', 'cleanup.py')


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _set_override(db, retention_period):
    db.table('sys.dataretention').insert(dict(table_fullname='sys.error', filter_column='__ins_ts',
                                              retention_period=retention_period))
    db.commit()


def _clear_overrides(db):
    db.table('sys.dataretention').deleteSelection(where='$table_fullname=:t', t='sys.error')
    db.commit()


def _load_cleanup(db):
    spec = importlib.util.spec_from_file_location('dataretention_cleanup', CLEANUP_ACTION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    batch = module.Main.__new__(module.Main)
    batch.db = db
    return batch


def _error_exists(db, pkey):
    return db.table('sys.error').query(where='$id=:pkey', pkey=pkey).count()


class TestRetentionOverrides:

    def test_removed_override_does_not_stick(self, db_sqlite):
        app = db_sqlite.application
        _set_override(db_sqlite, 5)
        try:
            assert app.retentionPolicy['sys.error']['retention_period'] == 5
        finally:
            _clear_overrides(db_sqlite)
        policy = app.retentionPolicy['sys.error']
        assert policy['retention_period'] == 60
        assert 'retention_period_custom' not in policy

    def test_override_leaves_default_policy_untouched(self, db_sqlite):
        app = db_sqlite.application
        _set_override(db_sqlite, 5)
        try:
            app.retentionPolicy
            default = app.defaultRetentionPolicy['sys.error']
        finally:
            _clear_overrides(db_sqlite)
        assert default['retention_period'] == 60
        assert 'retention_period_custom' not in default

    def test_empty_custom_retention_removes_override(self, db_sqlite):
        app = db_sqlite.application
        row = dict(table_fullname='sys.error', filter_column='__ins_ts',
                   retention_period_default=60, retention_period_custom=90)
        try:
            app.saveRetentionPolicy({'sys.error': row})
            assert app.retentionPolicy['sys.error']['retention_period'] == 90
            row['retention_period_custom'] = None
            app.saveRetentionPolicy({'sys.error': row})
            assert db_sqlite.table('sys.dataretention').query(where='$table_fullname=:t',
                                                              t='sys.error').count() == 0
            policy = app.retentionPolicy['sys.error']
            assert policy['retention_period'] == 60
            assert 'retention_period_custom' not in policy
        finally:
            _clear_overrides(db_sqlite)


class TestCleanupAction:

    def test_every_batch_step_has_a_handler(self, db_sqlite):
        batch = _load_cleanup(db_sqlite)
        for step in batch.batch_steps.split(','):
            assert callable(getattr(batch, 'step_%s' % step, None))

    def test_steps_delete_only_expired_records(self, db_sqlite):
        tbl = db_sqlite.table('sys.error')
        expired = tbl.newrecord(assignId=True, description='expired',
                                __ins_ts=datetime.now() - timedelta(days=70))
        tbl.raw_insert(expired)
        recent = tbl.newrecord(assignId=True, description='recent')
        tbl.insert(recent)
        db_sqlite.commit()
        batch = _load_cleanup(db_sqlite)
        for step in batch.batch_steps.split(','):
            getattr(batch, 'step_%s' % step)()
        assert _error_exists(db_sqlite, expired['id']) == 0
        assert _error_exists(db_sqlite, recent['id']) == 1
