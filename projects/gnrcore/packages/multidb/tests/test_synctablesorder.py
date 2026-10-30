# encoding: utf-8
"""Sync order of the tables in Package.checkFullSyncTables_do.

The order starts from tablesMasterIndex, which ignores deferred relations;
every table is committed in the stores right after its sync, so a table with
a deferred foreign key must follow the table it points to. The model is a
real GnrSqlDb model: dependencies and the master index are the framework's own.
"""

import importlib.util
import types
from pathlib import Path

from gnr.sql.gnrsql import GnrSqlDb

MAIN_PY = Path(__file__).resolve().parents[1] / 'main.py'
_spec = importlib.util.spec_from_file_location('multidb_main_syncorder_under_test', MAIN_PY)
multidb_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(multidb_main)


def build_db():
    db = GnrSqlDb()
    pkg = db.packageSrc('lkp')
    link = pkg.table('link', pkey='id')
    link.column('id', size='22')
    link.column('target_id', size='22').relation('target.id', mode='foreignkey',
                                                 onDelete='cascade', deferred=True)
    pos = pkg.table('pos', pkey='id')
    pos.column('id', size='22')
    pos.column('account_id', size='22').relation('account.id', mode='foreignkey',
                                                 onDelete='setnull')
    target = pkg.table('target', pkey='id')
    target.column('id', size='22')
    target.column('kind_id', size='22').relation('kind.id', mode='foreignkey',
                                                 onDelete='raise')
    kind = pkg.table('kind', pkey='id')
    kind.column('id', size='22')
    account = pkg.table('account', pkey='id')
    account.column('id', size='22')
    loop_a = pkg.table('loop_a', pkey='id')
    loop_a.column('id', size='22')
    loop_a.column('loop_b_id', size='22').relation('loop_b.id', mode='foreignkey',
                                                   onDelete='setnull')
    loop_b = pkg.table('loop_b', pkey='id')
    loop_b.column('id', size='22')
    loop_b.column('loop_a_id', size='22').relation('loop_a.id', mode='foreignkey',
                                                   onDelete='setnull')
    db.startup()
    return db


def sync_order(db, tables):
    return multidb_main.Package.syncTablesOrder(types.SimpleNamespace(db=db), tables)


def master_order(db):
    return list(db.tablesMasterIndex()['_index_'].digest('#a.tbl'))


def test_master_index_puts_deferred_before_target():
    order = master_order(build_db())
    assert order.index('lkp.link') < order.index('lkp.target')
    assert order.index('lkp.pos') < order.index('lkp.account')


def test_deferred_foreign_key_follows_its_target():
    db = build_db()
    order = sync_order(db, master_order(db))
    assert order.index('lkp.target') < order.index('lkp.link')
    assert order.index('lkp.account') < order.index('lkp.pos')
    assert order.index('lkp.kind') < order.index('lkp.target')


def test_tables_outside_the_list_do_not_block():
    db = build_db()
    assert sync_order(db, ['lkp.link', 'lkp.pos']) == ['lkp.link', 'lkp.pos']


def test_deferred_cycle_keeps_master_order():
    db = build_db()
    tables = [t for t in master_order(db) if t.startswith('lkp.loop_')]
    assert sync_order(db, tables) == tables
