import os
from gnr.sql.gnrsqlmigration import SqlMigrator,json_equal
from gnr.sql.gnrsql import GnrSqlDb
from .common import BaseGnrSqlTest


class TestGnrSqlMigration(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        cls.db.createDb(cls.dbname)
        cls.db.startup()
        cls.migrator = SqlMigrator(cls.db)

    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_gnrsqlmigration'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password")
                          )
        
    def createTestPackage(self):
        self.db.model.src.package('test', sqlschema='test')

    def createTableRecipe(self):
        pkg = self.db.package('test')
        tbl = pkg.table('recipe',pkey='code')
        tbl.column('code',size='5')
        tbl.column('description')

    def test_extractOrm(self):
        self.createTestPackage()
        self.createTableRecipe()


    def test_addingTable(self):
        db = self.migrator.application.db
        pkg = db.package('mig')
        tbl = pkg.table('ingredient',pkey='id')
        tbl.column('id',size='22')
        tbl.colmmn('description')
        assert not json_equal(self.migrator.sqlStructure,self.migrator.ormStructure),'Struct must be different'

