"""sysRecord(currentConnection=True) works inside the caller's transaction (issue #1621).

By default a missing sysRecord is created and committed on the ``system``
connection, which cannot see the caller's uncommitted rows and waits on
their locks. With ``currentConnection=True`` the lookup and the creation run
on the current connection and roll back with it.
"""
import _thread

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _system_in_transaction(db):
    connections = db._connections.get(_thread.get_ident(), {})
    connection = connections.get((db.rootstore, 'system'))
    return connection is not None and connection.get_transaction_status() != 0


def test_adopts_an_uncommitted_row_of_the_caller(db_pg):
    db = db_pg
    tbl = db.table('adm.language')
    assert not tbl.query(where='$code=:c', c='it').fetch()
    tbl.insert(tbl.newrecord(code='it', name='Italiano'))
    record = tbl.sysRecord('it', currentConnection=True)
    assert record['code'] == 'it'
    assert record['__syscode'] == 'it'
    assert not _system_in_transaction(db)
    db.rollback()
    assert not tbl.query(where='$code=:c', c='it').fetch()


def test_creates_on_the_current_connection_and_rolls_back(db_pg):
    db = db_pg
    tbl = db.table('adm.language')
    record = tbl.sysRecord('en', currentConnection=True)
    assert record['code'] == 'en'
    assert tbl.query(where='$__syscode=:c', c='en').fetch()
    assert not _system_in_transaction(db)
    db.rollback()
    assert not tbl.query(where='$code=:c', c='en').fetch()


def test_default_still_creates_and_commits_on_system(db_pg):
    db = db_pg
    tbl = db.table('adm.language')
    record = tbl.sysRecord('en')
    assert record['code'] == 'en'
    db.rollback()
    assert tbl.query(where='$__syscode=:c', c='en').fetch()


def test_default_does_not_cache_an_uncommitted_row(db_pg):
    db = db_pg
    tbl = db.table('adm.language')
    tbl.sysRecord('it', currentConnection=True)
    assert tbl.sysRecord('it')['code'] == 'it'
    db.rollback()
    record = tbl.sysRecord('it')
    assert record['code'] == 'it'
    db.rollback()
    assert tbl.query(where='$__syscode=:c', c='it').fetch()
