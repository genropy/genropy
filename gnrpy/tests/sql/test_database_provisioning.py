"""Provisioning regressions against real PostgreSQL connections and processes."""
import copy
import importlib.util
import multiprocessing
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from gnr.app.gnrapp import GnrSqlAppDb
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.adapters._gnrbaseadapter import DbAdapterException
from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException
from .common import get_pg_config, MockApplication, MockCache


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
def db(request, pg_config):
    name = 'gnr_provision_' + uuid4().hex[:12]
    db = GnrSqlDb(implementation=request.param, dbname=name, **pg_config)
    db.createDb(name, template='template0')
    try:
        yield db
    finally:
        db.closeConnection()
        db.dropDb(name)


def test_manager_connections_do_not_block_creation(db):
    with closing(db.adapter.connection(manager=True)) as first, \
            closing(db.adapter.connection(manager=True)), \
            closing(db.adapter.connection(manager=True)):
        with closing(first.cursor()) as cursor:
            cursor.execute('SELECT current_database()')
            assert cursor.fetchone()[0] == 'postgres'
        name = db.dbname + '_child'
        db.createDb(name)
        try:
            assert db.adapter.dbExists(name)
        finally:
            db.dropDb(name)


def test_template0_can_be_selected_with_busy_template1(db, pg_config):
    source = GnrSqlDb(implementation=db.implementation, dbname='template1', **pg_config)
    with closing(source.adapter.connect()):
        name = db.dbname + '_clean'
        db.createDb(name, template='template0')
        try:
            assert db.adapter.dbExists(name)
        finally:
            db.dropDb(name)


def test_creation_error_preserves_postgres_cause(db):
    with pytest.raises(DbAdapterException) as error:
        db.createDb(db.dbname)
    assert error.value.__cause__ is not None
    assert 'already exists' in str(error.value)


def test_failed_owned_queries_close_connections(db, monkeypatch):
    opened = []
    open_manager = db.adapter._managerConnection

    def tracked_manager():
        connection = open_manager()
        opened.append(connection)
        return connection
    monkeypatch.setattr(db.adapter, '_managerConnection', tracked_manager)
    errors = []
    for method in (db.adapter.raw_fetch, db.adapter.execute):
        try:
            method('SELECT 1 / 0', manager=True)
        except Exception as error:
            errors.append(error)  # Keep tracebacks alive: GC must not own cleanup.
    assert len(errors) == 2
    assert len(opened) == 2
    assert all(connection.closed for connection in opened)


def _hold_lock(config, implementation, dbname, pipe):
    db = GnrSqlDb(implementation=implementation, dbname=dbname, **config)
    with db.adapter.databaseLock(dbname):
        pipe.send('locked')
        pipe.recv()


def test_lock_excludes_another_process_and_survives_commits(db, pg_config):
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    process = context.Process(target=_hold_lock,
                              args=(pg_config, db.implementation, db.dbname, child))
    process.start()
    try:
        assert parent.poll(15)
        assert parent.recv() == 'locked'
        db.commit()
        with pytest.raises(DbAdapterException, match='already running'):
            with db.adapter.databaseLock(db.dbname):
                pytest.fail('Concurrent process acquired the same lock')
    finally:
        if process.is_alive():
            parent.send('release')
        process.join(15)
        if process.is_alive():
            process.terminate()
            process.join()
        parent.close()
        child.close()
    assert process.exitcode == 0
    with db.adapter.databaseLock(db.dbname):
        pass


def test_lock_is_released_after_worker_termination(db, pg_config):
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    process = context.Process(target=_hold_lock,
                              args=(pg_config, db.implementation, db.dbname, child))
    process.start()
    try:
        assert parent.poll(15)
        assert parent.recv() == 'locked'
    finally:
        process.terminate()
        process.join(15)
        parent.close()
        child.close()
    with db.adapter.databaseLock(db.dbname):
        pass


def _storetable_class():
    path = Path(__file__).resolve().parents[3] / 'projects/gnrcore/packages/multidb/lib/storetable.py'
    spec = importlib.util.spec_from_file_location('provisioning_storetable', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.StoreTable


@pytest.fixture
def store_db(pg_config, tmp_path):
    app = MockApplication()
    app.experimentalFlag = lambda *args: False
    app.onDbCommitted = lambda: None
    app.notifyDbEvent = lambda *args, **kwargs: None
    app.cache = MockCache()
    app.instanceFolder = str(tmp_path)
    app.config = Bag({'db?reuse_relation_tree': False,
                      'db?auto_static_enabled': False, 'packages': Bag()})
    app.config['packages'].setItem('hosting', None, storetable='hosting.workspace', prefix='provision')
    name = 'gnr_provision_' + uuid4().hex[:12]
    db = GnrSqlAppDb(application=app, implementation='postgres', dbname=name, **pg_config)
    app.db = db
    db.inTransactionDaemon = False
    pkg = db.model.src.package('hosting', sqlschema='hosting')
    table = pkg.table('workspace', pkey='id', multidb='one', db_creation_template='template0')
    table.column('id', dtype='A', size=':22')
    table.column('dbstore', dtype='A', size=':30')
    table.column('dbtemplate', dtype='A')
    table.column('startup_data_ts', dtype='DHZ')
    table.column('provisioning_status', dtype='A', size=':20')
    table.column('provisioning_error', dtype='T')
    payload = pkg.table('payload', pkey='id')
    payload.column('id', dtype='A', size=':22')
    payload.column('amount', dtype='I')
    db.tableMixin('hosting.workspace', _storetable_class())
    db.startup()
    db.createDb(name, template='template0')
    # Track exact names owned by this fixture; never sweep by prefix.
    children = []
    try:
        db.model.check(applyChanges=True)
        yield db, children
    finally:
        db.closeConnection()
        for child in children:
            if db.adapter.dbExists(child):
                db.dropDb(child)
        db.dropDb(name)


def test_activation_and_repeat_are_safe(store_db, pg_config):
    db, children = store_db
    table = db.table('hosting.workspace')
    name = uuid4().hex[:12]
    children.append(db.multidb_prefix + name)
    table.insert(dict(id=name, dbstore=name))
    db.commit()
    template = GnrSqlDb(implementation='postgres', dbname='template1', **pg_config)
    with closing(template.adapter.connect()):
        table.multidb_activateDbstore(name)
    assert table.record(pkey=name).output('dict')['provisioning_status'] == 'ready'
    assert name in db.dbstores
    with db.tempEnv(storename=name):
        db.adapter.execute('ALTER TABLE hosting.hosting_payload DROP COLUMN amount', autoCommit=True)
    table.multidb_activateDbstore(name)
    assert table.record(pkey=name).output('dict')['startup_data_ts'] is None
    with db.tempEnv(storename=name):
        assert 'amount' in [col['name'] for col in db.adapter.getColInfo('hosting_payload', 'hosting')]


def test_activation_while_locked_is_a_business_error(store_db, pg_config):
    db, children = store_db
    table = db.table('hosting.workspace')
    name = uuid4().hex[:12]
    table.insert(dict(id=name, dbstore=name))
    db.commit()
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    process = context.Process(target=_hold_lock,
                              args=(pg_config, 'postgres', db.multidb_prefix + name, child))
    process.start()
    try:
        assert parent.poll(15)
        assert parent.recv() == 'locked'
        with pytest.raises(GnrSqlBusinessLogicException, match='another request'):
            table.multidb_activateDbstore(name)
    finally:
        if process.is_alive():
            parent.send('release')
        process.join(15)
        parent.close()
        child.close()
    assert table.record(pkey=name).output('dict')['provisioning_status'] is None


def test_failed_create_can_be_retried(store_db, monkeypatch):
    db, children = store_db
    table = db.table('hosting.workspace')
    name = uuid4().hex[:12]
    children.append(db.multidb_prefix + name)
    # dbtemplate names a startup-data archive and must not reach CREATE DATABASE.
    table.insert(dict(id=name, dbstore=name, dbtemplate='startup_archive'))
    db.commit()
    monkeypatch.setitem(table.attributes, 'db_creation_template', 'gnr_missing_template')
    with pytest.raises(Exception, match='gnr_missing_template'):
        table.multidb_activateDbstore(name)
    record = table.record(pkey=name).output('dict')
    assert record['provisioning_status'] == 'failed'
    assert record['provisioning_error'].startswith('create:')
    assert name not in db.dbstores
    assert not db.adapter.dbExists(children[0])
    monkeypatch.undo()
    table.multidb_activateDbstore(name)
    record = table.record(pkey=name).output('dict')
    assert record['provisioning_status'] == 'ready'
    assert record['provisioning_error'] is None
    assert record['startup_data_ts'] is None


def test_failed_schema_resumes_without_marking_data_initialized(store_db):
    db, children = store_db
    table = db.table('hosting.workspace')
    name = uuid4().hex[:12]
    dbname = db.multidb_prefix + name
    children.append(dbname)
    table.insert(dict(id=name, dbstore=name, provisioning_status='creating'))
    db.commit()
    db.createDb(dbname, template='template0')
    # A real incompatible value makes PostgreSQL reject the schema migration.
    db.stores_handler.add_auxstore(name, dbattr=dict(dbname=dbname))
    with db.tempEnv(storename=name):
        db.adapter.execute("CREATE SCHEMA hosting; "
                           "CREATE TABLE hosting.hosting_payload (id varchar(22) PRIMARY KEY, amount text); "
                           "INSERT INTO hosting.hosting_payload VALUES ('keep', 'invalid')", autoCommit=True)
    db.stores_handler.auxstores.pop(name)
    with pytest.raises(Exception):
        table.multidb_activateDbstore(name)
    record = table.record(pkey=name).output('dict')
    assert record['provisioning_status'] == 'failed'
    assert record['provisioning_error'].startswith('align:')
    assert name not in db.dbstores
    assert name not in db.auxstores
    assert db.adapter.dbExists(dbname)
    db.stores_handler.add_auxstore(name, dbattr=dict(dbname=dbname))
    with db.tempEnv(storename=name):
        db.adapter.execute("UPDATE hosting.hosting_payload SET amount='7'; "
                           "ALTER TABLE hosting.hosting_payload ALTER COLUMN amount TYPE integer USING amount::integer",
                           autoCommit=True)
    db.stores_handler.auxstores.pop(name)
    table.multidb_activateDbstore(name)
    record = table.record(pkey=name).output('dict')
    assert record['provisioning_status'] == 'ready'
    assert record['startup_data_ts'] is None
    with db.tempEnv(storename=name):
        assert db.table('hosting.payload').record(pkey='keep').output('dict')['amount'] == 7


def test_initialized_store_is_not_initialized_twice(store_db):
    db, children = store_db
    table = db.table('hosting.workspace')
    name = uuid4().hex[:12]
    timestamp = table.newUTCDatetime()
    table.insert(dict(id=name, dbstore=name, provisioning_status='ready', startup_data_ts=timestamp))
    db.commit()
    table.multidb_setStartupData(name)
    assert table.record(pkey=name).output('dict')['startup_data_ts'] == timestamp


def test_another_pod_refreshes_its_independent_store_cache(store_db, pg_config, monkeypatch):
    db, children = store_db
    other_app = copy.copy(db.application)
    other_app.cache = MockCache()

    def shared_invalidation(key):
        pytest.fail('A periodic refresh must not invalidate the shared cache')
    monkeypatch.setattr(other_app.cache, 'updatedItem', shared_invalidation)
    other = GnrSqlAppDb(application=other_app, implementation='postgres',
                        dbname=db.dbname, **pg_config)
    other.inTransactionDaemon = False
    other.loadModel(db.model.src.toXml())
    other.startup()
    try:
        assert other.dbstores == {}
        name = uuid4().hex[:12]
        children.append(db.multidb_prefix + name)
        table = db.table('hosting.workspace')
        table.insert(dict(id=name, dbstore=name))
        db.commit()
        table.multidb_activateDbstore(name)
        assert other_app.cache.getItem('MULTI_DBSTORES') == {}
        other.stores_handler._dbstores_checked_at -= 6
        assert name in other.dbstores
    finally:
        other.closeConnection()
