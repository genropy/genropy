import datetime
import tempfile
import locale

import pytest

from gnr.sql import gnrsql as gs
from .common import BaseGnrSqlTest

class MockApplication(object):
    debug = True
    config = { "db?reuse_relation_tree": False,
               "db?auto_static_enabled": False}
    localizer = False
    instanceFolder = None
    def checkResourcePermission(self, deletable, tags, test=True):
        return test
    
class TestGnrSql(BaseGnrSqlTest):

    def test_generic_attrs(self):
        db = gs.GnrSqlDb()
        assert isinstance(db.tempEnv(), gs.TempEnv)

        # environment
        db.clearCurrentEnv()
        assert not db.currentEnv
        db.currentEnv = dict(a=1,b=2)
        assert "a" in db.currentEnv
        db.clearCurrentEnv()
        assert not db.currentEnv

        db.updateEnv(babbala=1)
        assert "babbala" in db.currentEnv
        db.clearCurrentEnv()
        assert "babbala" not in db.currentEnv
        db.updateEnv(_excludeNoneValues=True, babbala=None, ragazzo=1)
        assert "babbala" not in db.currentEnv
        assert "ragazzo" in db.currentEnv
        db.updateEnv(babbala=None)
        assert "babbala" in db.currentEnv
        db.clearCurrentEnv()
        assert "babbala" not in db.currentEnv
        assert "ragazzo" not in db.currentEnv

        test_store = "test1"
        db.use_store(test_store)
        assert "storename" in db.currentEnv
        with pytest.raises(KeyError):
            a = db.get_dbname()
        db.clearCurrentEnv()
        assert db.get_dbname() == "mydb"

        # rootstore/currentstore
        assert db.usingRootstore()
        db.use_store(test_store)
        assert not db.usingRootstore()
        db.clearCurrentEnv()
        assert db.usingRootstore()

        # connectioname
        assert db.usingMainConnection()
        db.updateEnv(connectionName="test1")
        assert not db.usingMainConnection()
        db.clearCurrentEnv()
        assert db.usingMainConnection()

        
        # workdate property
        assert db.workdate == datetime.date.today()
        test_date = datetime.date(1970,1,1)
        db.workdate = test_date
        assert db.workdate == test_date
        db.clearCurrentEnv()
        assert db.workdate == datetime.date.today()

        # locale property
        current_locale = locale.getlocale()[0]
        assert db.locale == current_locale
        db.locale = "it_IT"
        assert db.locale == "it_IT"
        db.clearCurrentEnv()
        assert db.locale == current_locale

        # the greatest test of all
        assert db.getUserConfiguration() is None

    def test_dbpar(self):
        db = gs.GnrSqlDb()
        r = db.dbpar("$HOME")
        assert r.startswith("/")

        r = db.dbpar(None)
        assert r is None

    def test_connections(self):
        db = gs.GnrSqlDb()
        assert not db._connections
        db.closeConnection()
        con = db.connection
        assert con is not None
        db.use_store("*")
        con = db.connection
        assert con is not None
        db.use_store("_main_db,_main_connection")
        con = db.connection
        assert con is not None
        db.use_store()
        assert "_main_db" in db.connectionKey()
        assert "_main_connection" in db.connectionKey()

        p = db.get_connection_params()
        for x in ['host','user','password','port']:
            assert p.get(x) == getattr(db, x)
        assert p.get("database") == db.dbname

    def test_stores(self):
        with tempfile.TemporaryDirectory() as tmp_instancefolder:
            test_store = "mydb2"
            application = MockApplication()
            application.instanceFolder = tmp_instancefolder
            db = gs.GnrSqlDb(application=application)
            db.stores_handler.add_store(test_store, dbattr=dict(dbname=test_store))
            p = db.get_connection_params(storename=test_store)
            assert p.get("database") == test_store
            # ensure it's not the default
            assert db.dbname != test_store
            db.use_store(test_store)
            assert db.get_dbname() == test_store
        
    def test_properties_without_app(self):
        db = gs.GnrSqlDb()
        assert db.debug is None
        assert not db.dbstores
        assert db.reuse_relation_tree is None
        assert db.auto_static_enabled is None
        assert db.localizer is not None

    def test_properties_with_app(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            application = MockApplication()
            application.instanceFolder = tmpdirname
            db = gs.GnrSqlDb(application=application)
            assert db.debug is True
            assert db.reuse_relation_tree is False
            assert db.auto_static_enabled is False
            assert db.localizer is False

    def test_dummy_localizer(self):
        l = gs.DbLocalizer()
        test_str = "ciao"
        assert l.translate(test_str) == test_str
        
