"""adm.preference.loadPreference closes the system connection it reads on (issue #1600).

The read runs on the ``system`` connection of the thread; left open, that
connection stayed idle in transaction until the end of the request.
"""
import _thread

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _in_transaction(connection):
    return connection.get_transaction_status() != 0


def _system_connection(db):
    connections = db._connections.get(_thread.get_ident(), {})
    return connections.get((db.rootstore, 'system'))


def test_load_preference_leaves_no_open_transaction(db_pg):
    db = db_pg
    tbl = db.table('adm.preference')
    tbl.loadPreference()
    assert tbl.loadPreference()['code'].strip() == '_mainpref_'
    connection = _system_connection(db)
    assert connection is not None
    assert not _in_transaction(connection)


def test_load_preference_for_update_keeps_the_lock(db_pg):
    db = db_pg
    tbl = db.table('adm.preference')
    tbl.loadPreference()
    tbl.loadPreference(for_update=True)
    connection = _system_connection(db)
    assert _in_transaction(connection)
    with db.tempEnv(connectionName='system'):
        db.rollback()
    assert not _in_transaction(connection)
