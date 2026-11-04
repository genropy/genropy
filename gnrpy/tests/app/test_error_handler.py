"""Tests for GnrApp.errorHandler persistence into sys.error.

Uses the shared test_invoice fixture (``db_sqlite``), whose instance
includes ``gnrcore:sys``.
"""

import pytest

from core.common import BaseGnrTest

from gnr.core.gnrbag import Bag, BagResolver


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


class FailingResolver(BagResolver):
    classKwargs = {'cacheTime': 0, 'readOnly': True}
    classArgs = []

    def load(self):
        raise RuntimeError('resolver failure')


def _handle(app, exc):
    return app.errorHandler(exception=exc, error_type='rpc_exception',
                            traceback=True, notify_user=True,
                            rpc_method='m', rpc_kwargs=Bag(a=1))


def _error_rows(db, error_id):
    db.closeConnection()
    return db.table('sys.error').query(
        columns='$description,$error_type,$rpc_method,$error_data',
        where='$error_code=:c', c=error_id).fetch()


def _error_row(db, pkey):
    db.closeConnection()
    return db.table('sys.error').query(
        columns='$description,$error_type,$username,$user_ip,$error_data',
        where='$id=:pkey', pkey=pkey).fetch()


class TestErrorHandlerPersistence:

    def test_plain_exception_is_written(self, db_sqlite):
        app = db_sqlite.application
        try:
            raise ValueError('plain failure')
        except ValueError as e:
            error_id = _handle(app, e)
        rows = _error_rows(db_sqlite, error_id)
        assert len(rows) == 1
        assert rows[0]['description'] == 'plain failure'
        assert rows[0]['error_type'] == 'rpc_exception'
        assert rows[0]['rpc_method'] == 'm'

    def test_exception_inside_resolver_is_written(self, db_sqlite):
        app = db_sqlite.application
        bag = Bag()
        bag.setItem('root', FailingResolver())
        try:
            bag['root']
        except RuntimeError as e:
            error_id = _handle(app, e)
        rows = _error_rows(db_sqlite, error_id)
        assert len(rows) == 1
        assert rows[0]['description'] == 'resolver failure'
        assert '*RESOLVER* FailingResolver' in str(rows[0]['error_data'])


class TestDeprecatedErrorWriters:

    def test_table_write_exception(self, db_sqlite):
        tbl = db_sqlite.table('sys.error')
        with pytest.warns(DeprecationWarning, match='writeException'):
            rec = tbl.writeException(description='legacy exception',
                                     traceback='legacy traceback',
                                     user='legacy_user', user_ip='10.0.0.1')
        assert rec['id']
        rows = _error_row(db_sqlite, rec['id'])
        assert len(rows) == 1
        assert rows[0]['description'] == 'legacy exception'
        assert rows[0]['error_type'] == 'EXC'
        assert rows[0]['username'] == 'legacy_user'
        assert rows[0]['user_ip'] == '10.0.0.1'

    def test_table_write_error(self, db_sqlite):
        tbl = db_sqlite.table('sys.error')
        with db_sqlite.tempEnv(legacy_marker='env in error_data'):
            db_sqlite.table('invc.invoice').query(
                columns='$id,@customer_id.account_name', limit=1).fetch()
            assert '_relations' in db_sqlite.currentEnv
            with pytest.warns(DeprecationWarning, match='writeError'):
                rec = tbl.writeError(description='legacy error', user='legacy_user',
                                     extra_info='kwargs in error_data')
        assert rec['id']
        rows = _error_row(db_sqlite, rec['id'])
        assert len(rows) == 1
        assert rows[0]['description'] == 'legacy error'
        assert rows[0]['error_type'] == 'ERR'
        assert rows[0]['username'] == 'legacy_user'
        error_data = str(rows[0]['error_data'])
        assert 'kwargs in error_data' in error_data
        assert 'env in error_data' in error_data

    def test_table_write_error_keeps_given_type(self, db_sqlite):
        tbl = db_sqlite.table('sys.error')
        with pytest.warns(DeprecationWarning):
            rec = tbl.writeError(description='typed error', error_type='WARN')
        rows = _error_row(db_sqlite, rec['id'])
        assert len(rows) == 1
        assert rows[0]['error_type'] == 'WARN'
