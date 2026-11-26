"""audit='external': the helpers of audit.event used by the history palettes.

The events are written at the commit of each ORM write.

The writes run on table audit_test.audited_item of the test_invoice_audit
instance (caption field code, Bag column details); PostgreSQL only.
"""

import pytest

from gnr.app.gnrapp import AuthTagStruct
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
    captions = db.table('audit.event').recordCaptions('audit_test.audited_item', [alive, deleted, 'nohistory'])
    assert captions == {alive: 'C1', deleted: 'C2b'}


def test_the_package_declares_the_default_history_tag(db):
    package = db.application.packages['audit']
    assert package.attributes['history_tags'] == 'auditHistory'
    root = AuthTagStruct.makeRoot()
    package.packageTags(root.branch('audit'))
    codes = [node.attr.get('code') for path, node in root.getIndex() if node.attr.get('tag') == 'authTag']
    assert codes == ['auditHistory']


def test_the_history_needs_the_history_tags(db):
    package = db.application.packages['audit']
    assert package.historyAllowed('user,auditHistory')
    assert not package.historyAllowed('user,admin,superadmin')
    assert not package.historyAllowed(None)


def test_an_instance_sets_its_own_history_tags(db, monkeypatch):
    package = db.application.packages['audit']
    monkeypatch.setitem(package.attributes, 'history_tags', 'auditor,superadmin')
    assert package.historyAllowed('user,superadmin')
    assert not package.historyAllowed('user,auditHistory')
