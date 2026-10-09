"""Reads on the system connection leave no transaction open (issue #1603).

``sys.external_token.use_token``, ``GnrWsgiSite._writeErrorRecord`` and
``adm.user.syncExternalUser`` read on the ``system`` connection of the
thread; left open, that connection stayed idle in transaction until the end
of the request, and ``syncExternalUser`` also held its row lock on
``adm_user``.

``_writeErrorRecord`` is checked here and not in the site tests: their
sqlite instance opens no transaction on a read.
"""
import _thread
from types import SimpleNamespace

import pytest

from core.common import BaseGnrTest
from gnr.web.gnrwsgisite import GnrWsgiSite


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _in_transaction(connection):
    return connection.get_transaction_status() != 0


def _system_connection(db):
    connections = db._connections.get(_thread.get_ident(), {})
    return connections.get((db.rootstore, 'system'))


@pytest.fixture(autouse=True)
def system_connection_out_of_transaction(db_pg):
    with db_pg.tempEnv(connectionName='system'):
        db_pg.rollback()


def _new_token(db, **kwargs):
    token = db.table('sys.external_token').create_token(page_path='/sys/test', method='test_method',
                                                        **kwargs)
    db.commit()
    return token


def test_use_token_without_max_usages_leaves_no_open_transaction(db_pg):
    db = db_pg
    token = _new_token(db)
    method, _, _, _ = db.table('sys.external_token').use_token(token)
    assert method == 'test_method'
    connection = _system_connection(db)
    assert connection is not None
    assert not _in_transaction(connection)


def test_use_token_with_invalid_token_leaves_no_open_transaction(db_pg):
    db = db_pg
    method, _, _, user = db.table('sys.external_token').use_token('not_a_token')
    assert method is None and user is None
    assert not _in_transaction(_system_connection(db))


def test_use_token_with_max_usages_records_the_use(db_pg):
    db = db_pg
    token = _new_token(db, max_usages=1)
    tbl = db.table('sys.external_token')
    assert tbl.use_token(token)[0] == 'test_method'
    assert not _in_transaction(_system_connection(db))
    assert db.table('sys.external_token_use').query(where='$external_token_id=:t', t=token).count() == 1
    assert tbl.use_token(token) == (None, None, None, None)
    assert not _in_transaction(_system_connection(db))


def _external_user(username, **kwargs):
    user = dict(username=username, firstname='Ext', lastname='User', email='ext@example.com')
    user.update(kwargs)
    return user


def _existing_user(db, username):
    tbl = db.table('adm.user')
    tbl.insert(tbl.newrecord(**_external_user(username)))
    db.commit()
    return tbl


def test_sync_external_user_unchanged_releases_the_lock(db_pg):
    db = db_pg
    tbl = _existing_user(db, 'ext_unchanged_1603')
    tbl.syncExternalUser(_external_user('ext_unchanged_1603'))
    assert not _in_transaction(_system_connection(db))


def test_sync_external_user_changed_updates_the_row(db_pg):
    db = db_pg
    tbl = _existing_user(db, 'ext_changed_1603')
    tbl.syncExternalUser(_external_user('ext_changed_1603', lastname='Renamed'))
    assert not _in_transaction(_system_connection(db))
    record = tbl.record(username='ext_changed_1603').output('dict')
    assert record['lastname'] == 'Renamed'


def test_write_error_record_leaves_no_open_transaction(db_pg):
    db = db_pg
    site = SimpleNamespace(db=db, errorHandler=db.application.errorHandler)
    rec = GnrWsgiSite._writeErrorRecord(site, description='system connection left clean',
                                        error_type='ERR')
    assert rec and rec['description'] == 'system connection left clean'
    assert not _in_transaction(_system_connection(db))
