"""Tests for adapter.vacuum() (issue #1286).

Verifies that:
- every postgres adapter inherits the one base implementation
- ``full`` selects VACUUM FULL ANALYZE, otherwise VACUUM ANALYZE
- the statement goes through a dedicated autocommit connection
- vacuum() succeeds while the db connection holds an open transaction
"""

import pytest

from gnr.sql.adapters._gnrbaseadapter import SqlDbAdapter
from gnr.sql.adapters import gnrpostgres, gnrpostgres3

IN_TRANSACTION = 2


class FakeDbRoot:
    fixed_schema = False


def _capture_execute(monkeypatch, adapter):
    calls = []

    def execute(sql, sqlargs=None, manager=False, autoCommit=False):
        calls.append((sql, autoCommit))

    monkeypatch.setattr(adapter, 'execute', execute)
    return calls


class TestVacuumStatement:

    def test_postgres_adapters_inherit_base_vacuum(self):
        assert gnrpostgres.SqlDbAdapter.vacuum is SqlDbAdapter.vacuum
        assert gnrpostgres3.SqlDbAdapter.vacuum is SqlDbAdapter.vacuum
        pg8000 = pytest.importorskip('gnr.sql.adapters.gnrpostgres8000', exc_type=ImportError)
        assert pg8000.SqlDbAdapter.vacuum is SqlDbAdapter.vacuum

    @pytest.mark.parametrize('full,expected', [
        (False, 'VACUUM ANALYZE invc.customer;'),
        (True, 'VACUUM FULL ANALYZE invc.customer;'),
    ])
    def test_statement_and_autocommit(self, monkeypatch, full, expected):
        adapter = SqlDbAdapter(FakeDbRoot())
        calls = _capture_execute(monkeypatch, adapter)
        adapter.vacuum(table='invc.customer', full=full)
        assert calls == [(expected, True)]

    def test_whole_database(self, monkeypatch):
        adapter = SqlDbAdapter(FakeDbRoot())
        calls = _capture_execute(monkeypatch, adapter)
        adapter.vacuum()
        assert calls == [('VACUUM ANALYZE ;', True)]


def _vacuum_inside_open_transaction(db):
    customer = db.table('invc.customer').model.sqlfullname
    product = db.table('invc.product').model.sqlfullname
    db.execute('SELECT 1;')
    assert int(db.connection.info.transaction_status) == IN_TRANSACTION
    try:
        db.adapter.vacuum(table=customer)
        db.adapter.vacuum(table=customer, full=True)
        db.vacuum(table=product, full=True)
        assert int(db.connection.info.transaction_status) == IN_TRANSACTION
    finally:
        db.rollback()


class TestVacuumPostgres:

    def test_vacuum_inside_transaction(self, db_pg):
        _vacuum_inside_open_transaction(db_pg)


class TestVacuumPostgres3:

    def test_vacuum_inside_transaction(self, db_pg3):
        _vacuum_inside_open_transaction(db_pg3)
