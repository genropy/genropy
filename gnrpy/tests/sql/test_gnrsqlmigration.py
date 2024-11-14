import os
from gnr.sql.gnrsqlmigration import SqlMigrator,json_equal
from gnr.sql.gnrsql import GnrSqlDb
from .common import BaseGnrSqlTest

import re

def normalize_sql(sql):
    """
    Normalizes SQL by removing extra whitespace and standardizing line breaks.
    
    Parameters:
        sql (str): The SQL string to normalize.
    
    Returns:
        str: Normalized SQL string.
    """
    # Remove extra spaces and newlines
    sql = re.sub(r'\s+', ' ', sql)  # Replaces multiple spaces/newlines with a single space
    return sql.strip()
class TestGnrSqlMigration(BaseGnrSqlTest):
    """
    Test suite for SQL migration operations in Genropy.
    Covers the creation of databases, schemas, tables, columns, 
    and constraints including primary and foreign keys, 
    along with additional operations such as renaming and indexing.
    """

    @classmethod
    def setup_class(cls):
        """
        Sets up the test class by initializing the database configuration
        and preparing the migrator for SQL migrations.
        """
        super().setup_class()
        cls.init()
        cls.src = cls.db.model.src
        cls.migrator = SqlMigrator(cls.db)
        cls.db.dropDb(cls.dbname)

    @classmethod
    def init(cls):
        """
        Initializes the test database connection with PostgreSQL settings.
        """
        cls.name = 'postgres'
        cls.dbname = 'test_gnrsqlmigration'
        cls.db = GnrSqlDb(
            implementation='postgres',
            host=cls.pg_conf.get("host"),
            port=cls.pg_conf.get("port"),
            dbname=cls.dbname,
            user=cls.pg_conf.get("user"),
            password=cls.pg_conf.get("password")
        )

    def checkChanges(self, expected_value=None):
        """
        Validates the expected SQL changes against actual changes.
        
        Parameters:
            expected_value (str): The expected SQL statement(s) as a string.
        
        If `expected_value` is '?', it will print the expected changes. If the actual
        SQL changes differ from `expected_value`, an assertion error will occur.
        """
        self.db.startup()
        self.migrator.toSql()
        
        if expected_value == '?':
            expected_changes = self.migrator.getChanges()
            print('Expected value:', expected_changes)
            return
        normalized_expected_value = normalize_sql(expected_value)
        changes = self.migrator.getChanges()
        normalized_changes = normalize_sql(expected_value)
        if normalized_changes != normalized_expected_value:
            print('Actual changes:', changes)
            print('ORM Structure:', self.migrator.ormStructure)
            print('SQL Structure:', self.migrator.sqlStructure)
            assert normalized_changes == normalized_expected_value, 'Mismatch in expected SQL commands.'
        else:
            self.migrator.applyChanges()
            self.migrator.toSql()
            changes = self.migrator.getChanges()
            assert not changes, 'Failed to execute SQL command as expected.'

    def test_01_create_db(self):
        """Tests database creation with the specified encoding."""
        check_value = """CREATE DATABASE "test_gnrsqlmigration" ENCODING 'UNICODE';\n"""
        self.checkChanges(check_value)

    def test_02_create_schema(self):
        """Tests schema creation in the database."""
        self.src.package('alfa', sqlschema='alfa')
        check_value = 'CREATE SCHEMA "alfa";'
        self.checkChanges(check_value)

    def test_03_create_table_nopkey(self):
        """Tests creation of a table without a primary key."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('code', size=':12')
        check_value = 'CREATE TABLE "alfa"."alfa_recipe" ("code" character varying(12));'
        self.checkChanges(check_value)

    def test_04_add_column(self):
        """Tests adding a new column to an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('description')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" \n ADD COLUMN "description" text;'
        self.checkChanges(check_value)

    def test_04b_add_indexed_column(self):
        """Tests adding a new column to an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('recipy_type',size=':2',indexed=True)
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" \n ADD COLUMN "recipy_type" character varying(2) ;\nCREATE INDEX idx_a540c475 ON "alfa"."alfa_recipe" USING btree (recipy_type) ;'
        self.checkChanges(check_value)

    def test_05_create_table_withpkey(self):
        """Tests creating a table with a primary key column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('description')
        check_value = 'CREATE TABLE "alfa"."alfa_ingredient" ("id" serial8 NOT NULL, "description" text, PRIMARY KEY (id));'
        self.checkChanges(check_value)

    def test_05b_add_primary_key(self):
        """Tests adding a primary key to an existing table by setting it as a table attribute."""
        pkg = self.src.package('alfa')
        pkg.table('recipe', pkey='code')  # Primary key defined as a table attribute
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" DROP CONSTRAINT IF EXISTS alfa_recipe_pkey;\nALTER TABLE "alfa"."alfa_recipe" ADD PRIMARY KEY (code);'
        self.checkChanges(check_value)


    def test_05c_create_table_withMultiplePkey(self):
        """Tests creating a table with a primary key column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row', pkey='composite_key')
        tbl.column('recipe_code', size=':12')
        tbl.column('recipe_line',dtype='L')
        tbl.compositeColumn('composite_key',columns='recipe_code,recipe_line')
        tbl.column('description')
        tbl.column('ingredient_id',dtype='L')
        check_value = 'CREATE TABLE "alfa"."alfa_recipe_row" ("recipe_code" character varying(12) , "recipe_line" bigint , "description" text , "ingredient_id" bigint , PRIMARY KEY (recipe_code,recipe_line));'
        self.checkChanges(check_value)


    #def test_06_add_foreign_key_singlecol(self):
    #    """
    #    Tests adding a foreign key constraint to a column.
    #    
    #    If the foreign key references a non-primary key field, an index
    #    should be automatically added to the referenced field to improve
    #    performance.
    #    """
    #    pkg = self.src.package('alfa')
    #    tbl = pkg.table('recipe_row')
    #    # add to the column recipe_code the relatio to the table recipe
    #    tbl.column('recipe_code', size=':12').relation('alfa.recipe.code', mode='foreignkey')
    #    self.checkChanges('?')

        
class ToDo:

    def test_06_modify_column_type(self):
        """Tests modifying the data type of an existing column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        tbl.column('description', dtype='varchar', size=':50')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" ALTER COLUMN "description" SET DATA TYPE character varying(50);'
        self.checkChanges(check_value)

    def test_07_rename_column(self):
        """Tests renaming an existing column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        tbl.rename_column('description', 'desc')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" RENAME COLUMN "description" TO "desc";'
        self.checkChanges(check_value)

    def test_08_rename_table(self):
        """Tests renaming an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        tbl.rename('ingredients')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" RENAME TO "alfa_ingredients";'
        self.checkChanges(check_value)

    def test_09_drop_column(self):
        """Tests dropping an existing column from a table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredients')
        tbl.drop_column('desc')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredients" DROP COLUMN "desc";'
        self.checkChanges(check_value)

    def test_10_drop_table(self):
        """Tests dropping a table from the schema."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredients')
        tbl.drop()
        check_value = 'DROP TABLE "alfa"."alfa_ingredients";'
        self.checkChanges(check_value)

    def test_11_add_foreign_key(self):
        """
        Tests adding a foreign key constraint to a column.
        
        If the foreign key references a non-primary key field, an index
        should be automatically added to the referenced field to improve
        performance.
        """
        pkg = self.src.package('alfa')
        tbl_ingredient = pkg.table('ingredient')
        
        # Defines a foreign key relation on a column, even if it may not be a primary key
        tbl_ingredient.column('recipe_id', dtype='integer').relation('alfa.recipe.id', mode='foreignkey')
        
        # Expected SQL for foreign key constraint and index creation if not a primary key
        check_value = (
            'ALTER TABLE "alfa"."alfa_ingredient" ADD CONSTRAINT fk_recipe FOREIGN KEY ("recipe_id") '
            'REFERENCES "alfa"."alfa_recipe" ("id");\n'
            'CREATE INDEX ON "alfa"."alfa_ingredient" ("recipe_id");'
        )
        self.checkChanges(check_value)

    def test_12_drop_foreign_key(self):
        """Tests dropping a foreign key constraint from a table."""
        pkg = self.src.package('alfa')
        tbl_ingredient = pkg.table('ingredient')
        tbl_ingredient.drop_foreign_key('fk_recipe')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" DROP CONSTRAINT fk_recipe;'
        self.checkChanges(check_value)

    def test_13_add_unique_constraint(self):
        """Tests adding a unique constraint on a column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.unique_constraint(['code'])
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" ADD CONSTRAINT unique_code UNIQUE ("code");'
        self.checkChanges(check_value)

    def test_14_drop_unique_constraint(self):
        """Tests dropping a unique constraint from a column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.drop_constraint('unique_code')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" DROP CONSTRAINT unique_code;'
        self.checkChanges(check_value)