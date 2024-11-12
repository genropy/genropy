import os
from gnr.sql.gnrsqlmigration import SqlMigrator,json_equal
from gnr.sql.gnrsql import GnrSqlDb
from .common import BaseGnrSqlTest


class TestGnrSqlMigration(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        cls.src = cls.db.model.src
        cls.migrator = SqlMigrator(cls.db)
        cls.db.dropDb(cls.dbname)

    @classmethod
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

    def checkChanges(self,check_value=None):
        self.db.startup()
        self.migrator.toSql()
        if check_value=='?':
            expectedChanges = self.migrator.getChanges()
            print('expected value',expectedChanges)
            return
        changes =  self.migrator.getChanges()
        if changes!=check_value:
            print('changes',changes)
            print('ormStructure',self.migrator.ormStructure)
            print('sqlStructure',self.migrator.ormStructure)
            assert changes==check_value,'Wrong sql command'
        else:
            self.migrator.applyChanges()
            self.migrator.toSql()
            changes = self.migrator.getChanges()
            assert not changes,'wrong sql command execution'

    def test_01_create_db(self):
        check_value = """CREATE DATABASE "test_gnrsqlmigration" ENCODING \'UNICODE\';\n"""
        self.checkChanges(check_value)
    
    def test_02_create_schema(self):
        self.src.package('alfa',sqlschema='alfa')
        check_value = 'CREATE SCHEMA "alfa";'
        self.checkChanges(check_value)

    def test_03_create_table_nopkey(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('code',size=':12')
        self.checkChanges('CREATE TABLE "alfa"."alfa_recipe" ("code" character varying(12) );')

    def test_04_add_column(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('description')
        self.checkChanges('?')

