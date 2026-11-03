"""audit='external': capture of every write by PostgreSQL triggers.

The writes run on table audit_test.audited_item of the test_invoice_audit
instance, which has audit='external' and a column with audit=False. The
triggers and the audit functions come from the sqlCode() scripts, so the
database is migrated with SqlMigrator before the tests; PostgreSQL only.
"""

import re

import pytest

from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.sql.gnrsqlmodel import DbModelSrc

from .conftest import _db_pg

AUDITED = 'audit_test.audit_test_audited_item'


@pytest.fixture(scope='module')
def db(request):
    for db in _db_pg(request, 'postgres', instance='test_invoice_audit'):
        migrator = SqlMigrator(db)
        migrator.prepareMigrationCommands()
        migrator.applyChanges()
        migrator.prepareMigrationCommands()
        assert not migrator.getChanges()
        yield db


def queue(db, pkey):
    return db.table('audit.queue').query(columns='*', where='$record_pkey = :pkey',
                                         pkey=pkey, order_by='$queue_id').fetch()


def version(db, pkey):
    return db.execute(f'SELECT __version FROM {AUDITED} WHERE id = :pkey',
                      dict(pkey=pkey)).fetchone()[0]


def insert_without_audit(db, pkey, code):
    """A record written before audit='external' was activated."""
    db.execute(f'ALTER TABLE {AUDITED} DISABLE TRIGGER USER')
    db.execute(f"INSERT INTO {AUDITED} (id, code, amount) VALUES (:pkey, :code, 1)",
               dict(pkey=pkey, code=code))
    db.execute(f'ALTER TABLE {AUDITED} ENABLE TRIGGER USER')
    db.commit()


def probe_table(**attributes):
    """A table source outside the model, to read the excluded columns."""
    root = DbModelSrc.makeRoot()
    root.child('package_list', 'packages')
    tbl = root.package('probe', sqlschema='probe').table('item', pkey='id', **attributes)
    for name in ('id', 'code', '__mod_ts', '__version', '__is_draft', 'hierarchical_code'):
        tbl.column(name)
    money = tbl.colgroup('money')
    money.column('amount', dtype='N')
    money.column('vat', dtype='N')
    tbl.attributes['draftField'] = '__is_draft'
    return tbl


def excluded_columns(db, **attributes):
    tbl = probe_table(**attributes)
    db.table('audit_test.audited_item').declareExternalAudit(tbl=tbl)
    return tbl.getNode('sql_scripts.s_0').attr['marker_excluded'].split(',')


def test_table_is_registered(db):
    member = db.table('audit.members').record(AUDITED).output('dict')
    assert member['tbl'] == 'audit_test.audited_item'
    assert member['pkey_column'] == 'id'
    assert member['activated_ts'] is not None
    assert member['touched_ts'] is None
    excluded = member['excluded_cols'].split(',')
    assert {'__version', '__mod_ts', '__mod_user', '__is_draft', 'last_invoice_date'} <= set(excluded)
    assert not {'id', 'code', 'amount', 'details', '__ins_ts', '__ins_user', '__del_ts'} & set(excluded)


def test_insert_update_delete(db):
    tbl = db.table('audit_test.audited_item')
    with db.tempEnv(user='mario'):
        record = dict(code='A1', description='first', amount=10)
        tbl.insert(record)
        db.commit()
        pkey = record['id']
        with tbl.recordToUpdate(pkey) as rec:
            rec['description'] = 'second'
        db.commit()
        with tbl.recordToUpdate(pkey) as rec:
            rec['last_invoice_date'] = '2026-11-03'
        db.commit()
        assert version(db, pkey) == 1
        tbl.delete(pkey)
        db.commit()
    ins, upd, dele = queue(db, pkey)
    assert (ins['op'], ins['version'], ins['username'], ins['sqlcommand']) == ('I', 0, 'mario', 'insert')
    assert re.search(r'test_audit_external\.test_insert_update_delete:\d+$', ins['caller'])
    assert ins['data']['code'] == 'A1'
    assert 'last_invoice_date' not in ins['data'] and '__mod_ts' not in ins['data']
    assert ins['old_full'] is None
    assert (upd['op'], upd['version'], upd['username'], upd['sqlcommand']) == ('U', 1, 'mario', 'update')
    assert upd['data'] == {'description': 'second'}
    assert upd['old_full'] is None
    assert (dele['op'], dele['version'], dele['username']) == ('D', 2, 'mario')
    assert dele['data']['description'] == 'second'


def test_first_update_of_a_record_written_before_activation(db):
    insert_without_audit(db, 'pre_update', 'P1')
    assert version(db, 'pre_update') is None
    with db.tempEnv(user='mario'):
        with db.table('audit_test.audited_item').recordToUpdate('pre_update') as rec:
            rec['amount'] = 2
        db.commit()
    [upd] = queue(db, 'pre_update')
    assert (upd['op'], upd['version']) == ('U', 1)
    assert upd['data'] == {'amount': 2}
    assert upd['old_full']['code'] == 'P1'
    assert float(upd['old_full']['amount']) == 1


def test_delete_of_a_record_written_before_activation(db):
    insert_without_audit(db, 'pre_delete', 'P2')
    with db.tempEnv(user='mario'):
        db.table('audit_test.audited_item').delete('pre_delete')
        db.commit()
    [dele] = queue(db, 'pre_delete')
    assert (dele['op'], dele['version']) == ('D', 1)
    assert dele['old_full']['code'] == 'P2'


def test_touch(db):
    insert_without_audit(db, 'pre_touch_1', 'T1')
    insert_without_audit(db, 'pre_touch_2', 'T2')
    members = db.table('audit.members')
    members.touch(block_size=1)
    for pkey, code in (('pre_touch_1', 'T1'), ('pre_touch_2', 'T2')):
        assert version(db, pkey) == 0
        [touch] = queue(db, pkey)
        assert (touch['op'], touch['version'], touch['data']) == ('U', 0, {})
        assert touch['old_full']['code'] == code
    assert members.record(AUDITED).output('dict')['touched_ts'] is not None
    queued = db.table('audit.queue').query().count()
    members.touch()
    assert db.table('audit.queue').query().count() == queued


def test_writes_that_bypass_the_orm_triggers(db):
    tbl = db.table('audit_test.audited_item')
    with db.tempEnv(user='mario'):
        record = dict(code='B1', amount=1)
        tbl.insert(record)
        db.commit()
        pkey = record['id']
        tbl.batchUpdate(dict(amount=5), _pkeys=[pkey])
        db.commit()
        db.execute(f"UPDATE {AUDITED} SET description = 'raw' WHERE id = :pkey", dict(pkey=pkey))
        db.commit()
        tbl.sql_deleteSelection(_pkeys=[pkey])
        db.commit()
    ins, batch, raw, dele = queue(db, pkey)
    assert (batch['op'], batch['version'], batch['username']) == ('U', 1, 'mario')
    assert float(batch['data']['amount']) == 5
    assert (raw['op'], raw['version'], raw['data']) == ('U', 2, {'description': 'raw'})
    assert (dele['op'], dele['version'], dele['username']) == ('D', 3, 'mario')


def test_write_outside_genropy_has_no_user(db):
    insert_without_audit(db, 'outside', 'O1')
    conn = db.adapter.connection()
    conn.cursor().execute(f"UPDATE {AUDITED} SET code = 'O2' WHERE id = 'outside'")
    conn.commit()
    conn.close()
    [upd] = queue(db, 'outside')
    assert (upd['op'], upd['version'], upd['data']) == ('U', 1, {'code': 'O2'})
    assert (upd['username'], upd['caller'], upd['sqlcommand']) == (None, None, None)


def test_default_excludes_system_fields(db):
    excluded = excluded_columns(db)
    assert set(excluded) == {'__version', '__mod_ts', '__is_draft', 'hierarchical_code'}


def test_whitelist_keeps_only_the_listed_columns(db):
    excluded = excluded_columns(db, audit_whitelist='code,money')
    assert set(excluded) == {'__version', 'id', '__mod_ts', '__is_draft', 'hierarchical_code'}


def test_blacklist_all_keeps_columns_with_audit_true(db):
    tbl = probe_table(audit_blacklist='*')
    tbl.getNode('columns.code').attr['audit'] = True
    db.table('audit_test.audited_item').declareExternalAudit(tbl=tbl)
    excluded = tbl.getNode('sql_scripts.s_0').attr['marker_excluded'].split(',')
    assert 'code' not in excluded
    assert {'id', 'amount', 'vat'} <= set(excluded)


def test_blacklist_of_a_colgroup(db):
    excluded = excluded_columns(db, audit_blacklist='money')
    assert {'amount', 'vat', '__mod_ts'} <= set(excluded)
    assert 'code' not in excluded


def test_column_attribute_wins_over_the_default(db):
    tbl = probe_table()
    tbl.getNode('columns.__mod_ts').attr['audit'] = True
    db.table('audit_test.audited_item').declareExternalAudit(tbl=tbl)
    assert '__mod_ts' not in tbl.getNode('sql_scripts.s_0').attr['marker_excluded'].split(',')


def test_both_lists_stop_the_model(db):
    with pytest.raises(ValueError, match='both'):
        excluded_columns(db, audit_whitelist='code', audit_blacklist='amount')


def test_unknown_name_stops_the_model(db):
    with pytest.raises(ValueError, match='nothere'):
        excluded_columns(db, audit_blacklist='nothere')


@pytest.mark.parametrize('mode', [True, 'lazy'])
def test_modes_true_and_lazy_keep_orm_triggers(db, mode):
    root = DbModelSrc.makeRoot()
    root.child('package_list', 'packages')
    root._dbmodel = db.model
    tbl = root.package('probe', sqlschema='probe').table('item', pkey='id', audit=mode)
    db.table('audit_test.audited_item').sysFields(tbl)
    attributes = tbl.getNode('columns.__version').attr
    assert attributes['onUpdating'] == 'setAuditVersionUpd'
    assert attributes['onInserting'] == 'setAuditVersionIns'
    assert 'sql_scripts' not in tbl
