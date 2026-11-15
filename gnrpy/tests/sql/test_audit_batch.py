"""audit='external': the events written from audit.queue.

An ORM write turns its queue rows into events at commit; the batch turns
into events the rows left in the queue by the writes outside the ORM.

The writes run on table audit_test.audited_item of the test_invoice_audit
instance; its column details is a Bag (dtype X). The database is migrated
with SqlMigrator, as in test_audit_external; PostgreSQL only.
"""

import threading
import time
from decimal import Decimal

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqlmigration import SqlMigrator

from .conftest import _db_pg

AUDITED = 'audit_test.audit_test_audited_item'
QUEUE = 'audit.audit_queue'
LOCK = "hashtext('audit.batch')"


@pytest.fixture(scope='module')
def db(request):
    for db in _db_pg(request, 'postgres', instance='test_invoice_audit'):
        migrator = SqlMigrator(db)
        migrator.prepareMigrationCommands()
        migrator.applyChanges()
        migrator.prepareMigrationCommands()
        assert not migrator.getChanges()
        yield db


def run(db, **kwargs):
    return db.table('audit.event').batch(**kwargs)


def events(db, pkey):
    return db.table('audit.event').query(columns='*,$data', where='$record_pkey = :pkey',
                                         pkey=pkey, order_by='$event_id').fetch()


def queued(db, pkey=None):
    where = 'record_pkey = :pkey' if pkey else 'true'
    return db.execute(f'SELECT count(*) FROM {QUEUE} WHERE {where}', dict(pkey=pkey)).fetchone()[0]


def insert_without_audit(db, pkey, code):
    """A record written before audit='external' was activated."""
    db.execute(f'ALTER TABLE {AUDITED} DISABLE TRIGGER USER')
    db.execute(f"INSERT INTO {AUDITED} (id, code, amount) VALUES (:pkey, :code, 1)",
               dict(pkey=pkey, code=code))
    db.execute(f'ALTER TABLE {AUDITED} ENABLE TRIGGER USER')
    db.commit()


def sql_update(db, pkey, **values):
    """An update outside the ORM: its row stays in the queue."""
    assignments = ', '.join(f'{name} = :{name}' for name in values)
    db.execute(f'UPDATE {AUDITED} SET {assignments} WHERE id = :pkey', dict(values, pkey=pkey))
    db.commit()


def details():
    bag = Bag()
    bag.setItem('address.city', 'Milano', checked=True)
    bag.setItem('address.zip', '20100')
    bag.setItem('note', 'first')
    return bag


def test_event_data_is_compressed_with_lz4(db):
    compression = db.execute("SELECT attcompression FROM pg_attribute "
                             "WHERE attrelid = 'audit.audit_event'::regclass "
                             "AND attname = 'data'").fetchone()[0]
    assert compression == 'l'


def test_history_of_a_record_and_of_a_bag_path(db):
    tbl = db.table('audit_test.audited_item')
    with db.tempEnv(user='mario'):
        record = dict(code='H1', description='first', amount=Decimal('10.25'), details=details())
        tbl.insert(record)
        db.commit()
        pkey = record['id']
        with tbl.recordToUpdate(pkey) as rec:
            rec['description'] = 'second'
        db.commit()
        with tbl.recordToUpdate(pkey) as rec:
            bag = Bag(rec['details'])
            bag.setItem('address.city', 'Roma', checked=False)
            bag.pop('note')
            bag.setItem('phone', '06123')
            rec['details'] = bag
        db.commit()
        tbl.delete(pkey)
        db.commit()
    assert queued(db, pkey) == 0
    first, upd, upd_details, dele = events(db, pkey)
    assert [(e['op'], e['version']) for e in (first, upd, upd_details, dele)] == \
        [('A', 0), ('U', 1), ('U', 2), ('D', 3)]
    assert Bag(first['data'])['description'] == 'first'
    assert Bag(upd['data']).asDict() == {'description': 'second'}
    diff = Bag(upd_details['data'])['details']
    assert diff['address.city'] == 'Roma'
    assert diff.getAttr('address.city', 'checked') is False
    assert 'zip' not in diff['address']
    assert diff.getAttr('note', '_deleted') is True
    assert diff['phone'] == '06123'
    history = db.table('audit.event').recordHistory('audit_test.audited_item', pkey)
    assert [h['state']['description'] if h['state'] else None for h in history] == \
        ['first', 'second', 'second', None]
    assert [h['state']['details.address.city'] if h['state'] else None for h in history] == \
        ['Milano', 'Milano', 'Roma', None]
    assert history[0]['state']['amount'] == Decimal('10.25')
    assert history[2]['state']['details.note'] is None
    assert history[2]['state']['details.address.zip'] == '20100'


def test_old_full_gives_an_A_event(db):
    insert_without_audit(db, 'pre_update', 'P1')
    insert_without_audit(db, 'pre_delete', 'P2')
    tbl = db.table('audit_test.audited_item')
    with tbl.recordToUpdate('pre_update') as rec:
        rec['amount'] = 2
    tbl.delete('pre_delete')
    db.commit()
    assert queued(db, 'pre_update') == 0 and queued(db, 'pre_delete') == 0
    assert [(e['op'], e['version']) for e in events(db, 'pre_update')] == [('A', 0), ('U', 1)]
    assert [(e['op'], e['version']) for e in events(db, 'pre_delete')] == [('A', 0), ('D', 1)]
    history = db.table('audit.event').recordHistory('audit_test.audited_item', 'pre_update')
    assert [h['state']['amount'] for h in history] == [Decimal(1), Decimal(2)]


def test_the_writes_of_a_transaction_defer_one_call(db):
    tbl = db.table('audit_test.audited_item')
    pkeys = []
    for code in ('T1', 'T2', 'T3'):
        record = dict(code=code)
        tbl.insert(record)
        pkeys.append(record['id'])
    db.commit()
    for pkey in pkeys:
        with tbl.recordToUpdate(pkey) as rec:
            rec['amount'] = 7
    deferred = db.currentEnv['%s_%s' % (db.QUEUE_DEFER_TO_COMMIT, db.connectionKey())]['_base_']
    callback = db.table('audit.event').eventsFromTransaction
    assert len([cb for cb, args, kwargs in deferred.values() if cb == callback]) == 1
    db.commit()
    for pkey in pkeys:
        assert queued(db, pkey) == 0
        assert [(e['op'], e['version']) for e in events(db, pkey)] == [('A', 0), ('U', 1)]


def test_a_row_left_in_the_queue_comes_first_in_the_chain(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='S1', amount=1)
    tbl.insert(record)
    db.commit()
    pkey = record['id']
    sql_update(db, pkey, amount=2)
    assert queued(db, pkey) == 1
    with tbl.recordToUpdate(pkey) as rec:
        rec['amount'] = 3
    db.commit()
    assert queued(db, pkey) == 0
    assert [(e['op'], e['version'], e['expected_version']) for e in events(db, pkey)] == \
        [('A', 0, None), ('U', 1, None), ('U', 2, None)]
    history = db.table('audit.event').recordHistory('audit_test.audited_item', pkey)
    assert [h['state']['amount'] for h in history] == [Decimal(1), Decimal(2), Decimal(3)]


def test_a_failed_conversion_fails_the_commit(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='X1')
    tbl.insert(record)
    db.commit()
    pkey = record['id']
    with tbl.recordToUpdate(pkey) as rec:
        rec['code'] = 'X2'
    db.execute(f"INSERT INTO {QUEUE} (ts, txid, tbl, record_pkey, op, version, data) "
               "VALUES (now(), txid_current(), 'nopkg.notable', 'broken', 'U', 1, '{}')")
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
    assert tbl.record(pkey, mode='dict')['code'] == 'X1'
    assert queued(db) == 0
    assert events(db, pkey) == []


def test_a_rollback_writes_no_events(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='N1')
    tbl.insert(record)
    db.commit()
    pkey = record['id']
    with tbl.recordToUpdate(pkey) as rec:
        rec['code'] = 'N2'
    db.rollback()
    db.commit()
    assert queued(db, pkey) == 0
    assert events(db, pkey) == []


def test_a_second_run_changes_nothing(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='R1')
    tbl.insert(record)
    db.commit()
    sql_update(db, record['id'], code='R2')
    assert run(db) == []
    assert [e['op'] for e in events(db, record['id'])] == ['A', 'U']
    count = db.table('audit.event').query().count()
    assert run(db) == []
    assert db.table('audit.event').query().count() == count


def test_a_row_committed_during_the_run_goes_to_the_next_run(db):
    tbl = db.table('audit_test.audited_item')
    for pkey in ('during_1', 'during_2', 'late'):
        tbl.insert(dict(id=pkey, code='C1'))
    db.commit()
    for pkey in ('during_1', 'during_2'):
        sql_update(db, pkey, code='C2')
    late = db.adapter.connection()
    late.cursor().execute(f"UPDATE {AUDITED} SET code = 'L1' WHERE id = 'late'")
    locker = db.adapter.connection()
    locker_cursor = locker.cursor()
    locker_cursor.execute('LOCK TABLE audit.audit_record_state IN ACCESS EXCLUSIVE MODE')
    result = {}

    def batch_thread():
        try:
            result['gaps'] = run(db, block_size=1)
        finally:
            db.closeConnection()

    thread = threading.Thread(target=batch_thread)
    thread.start()
    deadline = time.time() + 30
    waiting = 0
    while not waiting and time.time() < deadline:
        locker_cursor.execute('SELECT count(*) FROM pg_locks WHERE NOT granted')
        waiting = locker_cursor.fetchone()[0]
    assert waiting, 'the batch never reached the locked state table'
    late.commit()
    late.close()
    locker.commit()
    locker.close()
    thread.join(30)
    assert result['gaps'] == []
    assert queued(db, 'late') == 1
    run(db)
    assert queued(db, 'late') == 0
    assert [(e['op'], e['version']) for e in events(db, 'late')] == [('A', 0), ('U', 1)]


def test_a_second_run_exits_while_one_holds_the_lock(db):
    holder = db.adapter.connection()
    holder.cursor().execute(f'SELECT pg_advisory_lock({LOCK})')
    try:
        tbl = db.table('audit_test.audited_item')
        record = dict(code='K1')
        tbl.insert(record)
        db.commit()
        sql_update(db, record['id'], code='K2')
        assert run(db) is None
        assert queued(db, record['id']) == 1
    finally:
        holder.close()
    assert run(db) == []
    assert queued(db, record['id']) == 0


def test_a_failed_run_leaves_the_queue_intact(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='F1')
    tbl.insert(record)
    db.commit()
    sql_update(db, record['id'], code='F2')
    db.execute(f"INSERT INTO {QUEUE} (ts, tbl, record_pkey, op, version, data) "
               "VALUES (now(), 'nopkg.notable', 'broken', 'I', 0, '{}')")
    db.commit()
    queue_count = queued(db)
    event_count = db.table('audit.event').query().count()
    with pytest.raises(Exception):
        run(db)
    assert queued(db) == queue_count
    assert db.table('audit.event').query().count() == event_count
    db.execute(f"DELETE FROM {QUEUE} WHERE record_pkey = 'broken'")
    db.commit()
    assert run(db) == []
    assert [e['op'] for e in events(db, record['id'])] == ['A', 'U']


def test_a_gap_is_reported(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='G1', amount=1)
    tbl.insert(record)
    db.commit()
    pkey = record['id']
    for amount in (2, 3, 4):
        sql_update(db, pkey, amount=amount)
    db.execute(f'DELETE FROM {QUEUE} WHERE record_pkey = :pkey AND version = 2', dict(pkey=pkey))
    db.commit()
    gaps = run(db)
    assert gaps == [dict(tbl='audit_test.audited_item', record_pkey=pkey, version=3,
                         expected_version=2)]
    first, upd, gap = events(db, pkey)
    assert (first['op'], first['expected_version'], upd['version'], upd['expected_version']) == \
        ('A', None, 1, None)
    assert (gap['version'], gap['expected_version']) == (3, 2)
