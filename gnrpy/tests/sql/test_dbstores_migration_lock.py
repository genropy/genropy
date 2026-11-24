"""Store discovery must not retain locks on the workspace table."""

from datetime import datetime
from uuid import uuid4

import pytest

from gnr.app.gnrapp import GnrSqlAppDb
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqlmigration import SqlMigrator

from .common import MockApplication, MockCache, get_pg_config


@pytest.fixture(scope='module')
def pg_config():
    config, server = get_pg_config()
    config.pop('database', None)
    try:
        yield config
    finally:
        if server:
            server.stop()


@pytest.fixture(params=['postgres', 'postgres3'])
def store_db(request, pg_config, tmp_path):
    app = MockApplication()
    app.experimentalFlag = lambda *args: False
    app.onDbCommitted = lambda: None
    app.notifyDbEvent = lambda *args, **kwargs: None
    app.cache = MockCache()
    app.instanceFolder = str(tmp_path)
    app.config = Bag({'db?reuse_relation_tree': False,
                      'db?auto_static_enabled': False, 'packages': Bag()})
    prefix = 'gnr_store_lock_' + uuid4().hex[:12]
    app.config['packages'].setItem('hosting', None,
                                   storetable='hosting.workspace', prefix=prefix)
    db = GnrSqlAppDb(application=app, implementation=request.param,
                    dbname=prefix + '_main', **pg_config)
    app.db = db
    db.inTransactionDaemon = False
    pkg = db.model.src.package('hosting', sqlschema='hosting')
    workspace = pkg.table('workspace', pkey='id', multidb='one',
                          logicalDeletionField='deleted_at',
                          partition_office_id='office_id')
    workspace.column('id', dtype='A', size=':22')
    workspace.column('office_id', dtype='A', size=':22')
    workspace.column('dbstore', dtype='A', size=':30')
    workspace.column('deleted_at', dtype='DH')
    workspace.column('provisioning_status', dtype='A', size=':20')
    workspace.column('description', dtype='T')
    payload = pkg.table('payload', pkey='id')
    payload.column('id', dtype='A', size=':22')
    payload.column('amount', dtype='I')
    db.startup()
    db.createDb(db.dbname, template='template0')
    child = db.multidb_prefix + 'tenant'
    try:
        db.createDb(child, template='template0')
        db.model.check(applyChanges=True)
        db.table('hosting.workspace').insert(
            dict(id='tenant', dbstore='tenant', provisioning_status='ready'))
        db.commit()
        db.closeConnection()
        yield db, child
    finally:
        db.closeConnection()
        if db.adapter.dbExists(child):
            db.dropDb(child)
        db.dropDb(db.dbname)


def test_store_discovery_does_not_block_schema_migration(store_db, monkeypatch):
    db, child = store_db
    table = db.table('hosting.workspace').model.sqlfullname
    db.adapter.execute(f'ALTER TABLE {table} DROP COLUMN description', autoCommit=True)
    # The migration opens another connection. Bound its wait so the regression
    # fails with PostgreSQL's lock error instead of hanging the test runner.
    monkeypatch.setenv('PGOPTIONS', '-c lock_timeout=500ms -c statement_timeout=5s')
    assert db.dbstores == {'tenant': dict(database=child)}
    migrator = SqlMigrator(db)
    migrator.prepareMigrationCommands()
    assert 'ADD COLUMN "description"' in migrator.getChanges()
    migrator.applyChanges()
    assert 'description' in {
        col['name'] for col in db.adapter.getColInfo('hosting_workspace', 'hosting')}


def test_store_discovery_preserves_pending_work(store_db):
    db, child = store_db
    payload = db.table('hosting.payload')
    payload.insert(dict(id='pending', amount=7))
    assert db.dbstores == {'tenant': dict(database=child)}
    assert payload.record(pkey='pending').output('dict')['amount'] == 7
    assert db.adapter.raw_fetch(
        'SELECT count(*) FROM hosting.hosting_payload')[0][0] == 0
    db.rollback()
    assert db.adapter.raw_fetch(
        'SELECT count(*) FROM hosting.hosting_payload')[0][0] == 0


@pytest.mark.parametrize('status,deleted,visible', [
    ('ready', False, True),
    (None, False, True),
    ('creating', False, False),
    ('failed', False, False),
    ('ready', True, False),
])
def test_store_discovery_keeps_workspace_filters(store_db, status, deleted, visible):
    db, child = store_db
    with db.table('hosting.workspace').recordToUpdate('tenant') as record:
        record['provisioning_status'] = status
        record['deleted_at'] = datetime.now() if deleted else None
    db.commit()
    expected = {'tenant': dict(database=child)} if visible else {}
    assert db.dbstores == expected


@pytest.mark.parametrize('env', [dict(current_office_id='other'),
                                 dict(allowed_office_id=('other',))])
def test_store_discovery_ignores_the_user_partition(store_db, env):
    db, child = store_db
    with db.tempEnv(**env):
        assert db.dbstores == {'tenant': dict(database=child)}
