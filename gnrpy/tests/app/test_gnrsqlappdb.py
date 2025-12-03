import tempfile

from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrSqlAppDb, DbStoresHandler
from gnrpy.tests.sql.common import MockApplication


class TestGnrSqlAppDb:
    """Tests for GnrSqlAppDb class"""

    def test_stores_handler_exists(self):
        """GnrSqlAppDb should have a stores_handler"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            assert db.stores_handler is not None
            assert isinstance(db.stores_handler, DbStoresHandler)

    def test_debug_from_application(self):
        """GnrSqlAppDb.debug should return application.debug"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            application.debug = True
            db = GnrSqlAppDb(application=application)
            assert db.debug is True

            application.debug = False
            assert db.debug is False

    def test_auxstores(self):
        """Test adding auxiliary stores"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            test_store = "mydb2"
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            db.stores_handler.add_auxstore(test_store, dbattr=dict(dbname=test_store))

            assert test_store in db.auxstores
            assert db.auxstores[test_store]['database'] == test_store

    def test_get_connection_params_for_store(self):
        """Test getting connection parameters for a specific store"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            test_store = "mydb2"
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            db.stores_handler.add_auxstore(test_store, dbattr=dict(dbname=test_store))

            p = db.get_connection_params(storename=test_store)
            assert p.get("database") == test_store
            # ensure it's not the default
            assert db.dbname != test_store

    def test_use_store(self):
        """Test using a store changes the database name"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            test_store = "mydb2"
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            db.stores_handler.add_auxstore(test_store, dbattr=dict(dbname=test_store))

            db.use_store(test_store)
            assert db.get_dbname() == test_store

    def test_multidb_config_empty(self):
        """Test multidb_config returns empty dict when no storetable configured"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)

            assert db.multidb_config == {}
            assert db.storetable is None

    def test_multidb_config_with_storetable(self):
        """Test multidb_config returns config when storetable is configured"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            # Configure a package with storetable
            application.config = Bag({
                'db?reuse_relation_tree': False,
                'db?auto_static_enabled': False,
                'dbstores': None,
                'packages': Bag()
            })
            application.config['packages'].setItem('testpkg', None,
                storetable='testpkg.store_table',
                prefix='test',
                multidomain=True
            )
            db = GnrSqlAppDb(application=application)

            assert db.multidb_config.get('storetable') == 'testpkg.store_table'
            assert db.multidb_config.get('prefix') == 'test'
            assert db.storetable == 'testpkg.store_table'
            assert db.multidb_prefix == 'test_'

    def test_multidb_config_caching(self):
        """Test multidb_config is cached after first access"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            application.config = Bag({
                'db?reuse_relation_tree': False,
                'db?auto_static_enabled': False,
                'dbstores': None,
                'packages': Bag()
            })
            application.config['packages'].setItem('testpkg', None,
                storetable='testpkg.store_table'
            )
            db = GnrSqlAppDb(application=application)

            # First access
            config1 = db.multidb_config
            # Second access should return cached value
            config2 = db.multidb_config
            assert config1 is config2

    def test_tenant_table(self):
        """Test tenant_table property"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            application.config = Bag({
                'db?reuse_relation_tree': False,
                'db?auto_static_enabled': False,
                'dbstores': None,
                'packages': Bag()
            })
            application.config['packages'].setItem('testpkg', None,
                tenant_table='testpkg.tenant'
            )
            db = GnrSqlAppDb(application=application)

            assert db.tenant_table == 'testpkg.tenant'


class TestDbStoresHandler:
    """Tests for DbStoresHandler class"""

    def test_init(self):
        """Test DbStoresHandler initialization"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            handler = DbStoresHandler(db)

            assert handler.db is db
            assert handler.auxstores == {}

    def test_add_auxstore_with_defaults(self):
        """Test add_auxstore uses db defaults for missing attributes"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            handler = DbStoresHandler(db)

            handler.add_auxstore('teststore', dbattr={'dbname': 'testdb'})

            store = handler.auxstores['teststore']
            assert store['database'] == 'testdb'
            assert store['host'] == db.host
            assert store['user'] == db.user
            assert store['password'] == db.password
            assert store['port'] == db.port

    def test_add_auxstore_with_custom_attrs(self):
        """Test add_auxstore with custom connection attributes"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = GnrSqlAppDb(application=application)
            handler = DbStoresHandler(db)

            handler.add_auxstore('teststore', dbattr={
                'dbname': 'testdb',
                'host': 'customhost',
                'user': 'customuser',
                'password': 'custompass',
                'port': 5433
            })

            store = handler.auxstores['teststore']
            assert store['database'] == 'testdb'
            assert store['host'] == 'customhost'
            assert store['user'] == 'customuser'
            assert store['password'] == 'custompass'
            assert store['port'] == 5433

    def test_init_with_dbstores_config(self):
        """Test DbStoresHandler loads stores from application config"""
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            # Configure dbstores in application config
            dbstores = Bag()
            dbstores.setItem('store1', None, dbname='db1', host='host1')
            dbstores.setItem('store2', None, dbname='db2', host='host2')
            application.config = Bag({
                'db?reuse_relation_tree': False,
                'db?auto_static_enabled': False,
                'dbstores': dbstores,
                'packages': Bag()
            })

            db = GnrSqlAppDb(application=application)
            handler = db.stores_handler

            assert 'store1' in handler.auxstores
            assert 'store2' in handler.auxstores
            assert handler.auxstores['store1']['database'] == 'db1'
            assert handler.auxstores['store1']['host'] == 'host1'
