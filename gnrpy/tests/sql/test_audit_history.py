"""audit='external': the helpers of audit.event used by the history palettes.

The writes run on table audit_test.audited_item of the test_invoice_audit
instance (caption field code, Bag column details); PostgreSQL only.
"""

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqlmigration import SqlMigrator

from .conftest import _db_pg


@pytest.fixture(scope='module')
def db(request):
    for db in _db_pg(request, 'postgres', instance='test_invoice_audit'):
        migrator = SqlMigrator(db)
        migrator.prepareMigrationCommands()
        migrator.applyChanges()
        yield db


def details(city):
    bag = Bag()
    bag.setItem('address.city', city)
    bag.setItem('note', 'first')
    return bag


def insert(db, code, city='Milano'):
    record = dict(code=code, description='first', details=details(city))
    db.table('audit_test.audited_item').insert(record)
    db.commit()
    return record['id']


def update_events(db, pkey):
    return db.table('audit.event').query(columns='$data', where="$record_pkey = :pkey AND $op = 'U'",
                                         pkey=pkey, order_by='$event_id').fetch()


def test_hidden_columns_are_system_fields_and_pkey(db):
    hidden = db.table('audit.event').displayHiddenColumns('audit_test.audited_item')
    assert {'id', '__ins_ts', '__version'} <= hidden
    assert 'code' not in hidden and 'details' not in hidden


def test_changed_paths_of_an_update(db):
    tbl = db.table('audit_test.audited_item')
    pkey = insert(db, 'P1')
    with tbl.recordToUpdate(pkey) as rec:
        rec['description'] = 'second'
    db.commit()
    with tbl.recordToUpdate(pkey) as rec:
        rec['details'] = details('Roma')
    db.commit()
    db.table('audit.event').batch()
    eventtbl = db.table('audit.event')
    changes = [eventtbl.changedPaths('audit_test.audited_item', row['data']) for row in update_events(db, pkey)]
    assert changes == [['description'], ['details.address.city']]


def test_captions_from_the_table_and_from_the_last_state(db):
    tbl = db.table('audit_test.audited_item')
    alive = insert(db, 'C1')
    deleted = insert(db, 'C2')
    with tbl.recordToUpdate(deleted) as rec:
        rec['code'] = 'C2b'
    db.commit()
    tbl.delete(tbl.record(deleted, mode='dict'))
    db.commit()
    db.table('audit.event').batch()
    captions = db.table('audit.event').recordCaptions('audit_test.audited_item', [alive, deleted, 'nohistory'])
    assert captions == {alive: 'C1', deleted: 'C2b'}
