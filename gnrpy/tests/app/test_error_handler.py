"""Tests for GnrApp.errorHandler persistence into sys.error.

Uses the shared test_invoice fixture (``db_sqlite``), whose instance
includes ``gnrcore:sys``.
"""

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
