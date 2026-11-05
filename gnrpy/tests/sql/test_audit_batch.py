"""audit='external': the batch that turns audit.queue into audit.event.

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
    assert run(db) == []
    assert queued(db) == 0
    ins, upd, upd_details, dele = events(db, pkey)
    assert [(e['op'], e['version']) for e in (ins, upd, upd_details, dele)] == \
        [('I', 0), ('U', 1), ('U', 2), ('D', 3)]
    assert (ins['username'], ins['sqlcommand']) == ('mario', 'insert')
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


def test_a_second_run_changes_nothing(db):
    tbl = db.table('audit_test.audited_item')
    tbl.insert(dict(code='R1'))
    db.commit()
    run(db)
    count = db.table('audit.event').query().count()
    assert run(db) == []
    assert db.table('audit.event').query().count() == count


def test_old_full_gives_an_A_event(db):
    insert_without_audit(db, 'pre_update', 'P1')
    insert_without_audit(db, 'pre_delete', 'P2')
    insert_without_audit(db, 'pre_touch', 'P3')
    tbl = db.table('audit_test.audited_item')
    with tbl.recordToUpdate('pre_update') as rec:
        rec['amount'] = 2
    tbl.delete('pre_delete')
    db.commit()
    db.table('audit.members').touch()
    assert run(db) == []
    assert [(e['op'], e['version']) for e in events(db, 'pre_update')] == [('A', 0), ('U', 1)]
    assert [(e['op'], e['version']) for e in events(db, 'pre_delete')] == [('A', 0), ('D', 1)]
    [touch] = events(db, 'pre_touch')
    assert (touch['op'], touch['version']) == ('A', 0)
    assert Bag(touch['data'])['code'] == 'P3'
    history = db.table('audit.event').recordHistory('audit_test.audited_item', 'pre_update')
    assert [h['state']['amount'] for h in history] == [Decimal(1), Decimal(2)]


def test_a_row_committed_during_the_run_goes_to_the_next_run(db):
    tbl = db.table('audit_test.audited_item')
    tbl.insert(dict(code='C1'))
    tbl.insert(dict(code='C2'))
    db.commit()
    late = db.adapter.connection()
    late.cursor().execute(f"INSERT INTO {AUDITED} (id, code) VALUES ('late', 'L1')")
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
    [ins] = events(db, 'late')
    assert (ins['op'], ins['version']) == ('I', 0)


def test_a_second_run_exits_while_one_holds_the_lock(db):
    holder = db.adapter.connection()
    holder.cursor().execute(f'SELECT pg_advisory_lock({LOCK})')
    try:
        tbl = db.table('audit_test.audited_item')
        record = dict(code='K1')
        tbl.insert(record)
        db.commit()
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
    [ins] = events(db, record['id'])
    assert ins['op'] == 'I'


def test_a_gap_is_reported(db):
    tbl = db.table('audit_test.audited_item')
    record = dict(code='G1', amount=1)
    tbl.insert(record)
    db.commit()
    pkey = record['id']
    for amount in (2, 3):
        with tbl.recordToUpdate(pkey) as rec:
            rec['amount'] = amount
        db.commit()
    db.execute(f'DELETE FROM {QUEUE} WHERE record_pkey = :pkey AND version = 1', dict(pkey=pkey))
    db.commit()
    gaps = run(db)
    assert gaps == [dict(tbl='audit_test.audited_item', record_pkey=pkey, version=2,
                         expected_version=1)]
    ins, upd = events(db, pkey)
    assert (ins['expected_version'], upd['version'], upd['expected_version']) == (None, 2, 1)
