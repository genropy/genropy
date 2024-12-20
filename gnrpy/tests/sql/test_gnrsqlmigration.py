import pytest
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.adapters import gnrpostgres, gnrpostgres3
from gnr.sql import AdapterCapabilities as Capabilities
from .common import BaseGnrSqlTest

import re

def normalize_sql(sql):
    """
    Normalizes SQL by removing extra whitespace, standardizing spacing around symbols, 
    and ensuring consistent formatting.

    Parameters:
        sql (str): The SQL string to normalize.

    Returns:
        str: Normalized SQL string.
    """
    # Replace multiple spaces and newlines with a single space
    sql = re.sub(r'\s+', ' ', sql)

    # Remove spaces around opening parentheses
    sql = re.sub(r'\s*\(\s*', '(', sql)

    # Remove spaces around closing parentheses
    sql = re.sub(r'\s*\)\s*', ')', sql)

    # Ensure a single space after commas
    sql = re.sub(r'\s*,\s*', ', ', sql)

    # Ensure no space before a semicolon
    sql = re.sub(r'\s*;\s*', ';', sql)

    # Trim leading and trailing spaces
    return sql.strip()

class BaseGnrSqlMigration(BaseGnrSqlTest):
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
        cls.migrator = SqlMigrator(cls.db,removeDisabled=False)
        cls.db.dropDb(cls.dbname)
            
    def checkChanges(self, expected_value=None,apply_only=False):
        """
        Validates the expected SQL changes against actual changes.
        
        Parameters:
            expected_value (str): The expected SQL statement(s) as a string.
        
        If `expected_value` is '?', it will print the expected changes. If the actual
        SQL changes differ from `expected_value`, an assertion error will occur.
        """
        self.db.startup()
        self.migrator.prepareMigrationCommands()
        if apply_only:
            self.migrator.applyChanges()
            return
        if expected_value == '?':
            expected_changes = self.migrator.getChanges()
            print('Expected value:', expected_changes)
            return
        normalized_expected_value = normalize_sql(expected_value)
        changes = self.migrator.getChanges()
        normalized_changes = normalize_sql(changes)
        if normalized_changes != normalized_expected_value:
            print('Actual changes:', changes)
            print('ORM Structure:', self.migrator.ormStructure)
            print('SQL Structure:', self.migrator.sqlStructure)
            assert normalized_changes == normalized_expected_value, 'Mismatch in expected SQL commands.'
        else:
            self.migrator.applyChanges()
            self.migrator.prepareMigrationCommands()
            changes = self.migrator.getChanges()
            if changes:
                print('unexpected changes',changes)
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

    def test_04d_add_numeric_column(self):
        """Tests adding a new column to an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('cost',dtype='N',size='14,2')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe" \n ADD COLUMN "cost" numeric(14,2) ;'
        self.checkChanges(check_value)

    def test_04b_add_indexed_columns(self):
        """Tests adding a new column to an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('ins_ts',dtype='DH',indexed=True)
        tbl.column('recipy_type',size=':2',indexed=True)

        check_value = 'ALTER TABLE "alfa"."alfa_recipe" \n ADD COLUMN "ins_ts" timestamp without time zone ,\nADD COLUMN "recipy_type" character varying(2) ;\nCREATE INDEX idx_f473bae1 ON "alfa"."alfa_recipe" USING btree (ins_ts) ;\nCREATE INDEX idx_490f54d9 ON "alfa"."alfa_recipe" USING btree (recipy_type) ;'
        self.checkChanges(check_value)

    def test_04c_add_unique_multiple_constraint(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('restaurant', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('name',size=':45')
        tbl.column('country',size='2')
        tbl.column('vat_number',size=':30')
        tbl.compositeColumn('international_vat',columns='country,vat_number',unique=True)
        check_value = 'CREATE TABLE "alfa"."alfa_restaurant"(\n "id" serial8 NOT NULL,\n "name" character varying(45),\n "country" character(2),\n "vat_number" character varying(30),\n PRIMARY KEY (id),\n CONSTRAINT "cst_703bf76b" UNIQUE ("country", "vat_number")\n);\nCREATE UNIQUE INDEX idx_91100f32 ON "alfa"."alfa_restaurant" USING btree (country, vat_number);'
        self.checkChanges(check_value)

    def test_05a_create_table_withpkey(self):
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

    def test_05c_create_table_withCompositePkey(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row', pkey='composite_key')
        tbl.column('recipe_code', size=':12')
        tbl.column('recipe_line',dtype='L')
        tbl.compositeColumn('composite_key',columns='recipe_code,recipe_line')
        tbl.column('description')
        tbl.column('ingredient_id',dtype='L')
        check_value = 'CREATE TABLE "alfa"."alfa_recipe_row" ("recipe_code" character varying(12) NOT NULL , "recipe_line" bigint NOT NULL , "description" text , "ingredient_id" bigint , PRIMARY KEY (recipe_code,recipe_line));'
        self.checkChanges(check_value)

    def test_05a_create_table_with_pkey_explicit_unique(self):
        """Tests creating a table with a primary key column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('company', pkey='code')
        tbl.column('code', size=':30',unique=True)
        tbl.column('description')
        check_value = 'CREATE TABLE "alfa"."alfa_company"(\n "code" character varying(30) NOT NULL,\n "description" text,\n PRIMARY KEY (code)\n);'
        self.checkChanges(check_value)

    def test_06_prepare_table(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_annotation', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('description')
        tbl.column('recipe_code', size=':12').relation('alfa.recipe.code',mode='foreignkey')
        tbl.column('recipe_line',dtype='L')
        tbl.compositeColumn('recipe_row_reference',columns='recipe_code,recipe_line')

        tbl = pkg.table('author', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('name',size=':45',unique=True)
        tbl.column('tax_code',size=':45')
        self.checkChanges(apply_only=True)

    def test_06a_add_relation_to_pk_single(self):
        """
        Tests adding a foreign key constraint to a column.
        
        If the foreign key references a non-primary key field, an index
        should be automatically added to the referenced field to improve
        performance.
        """
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row')
        # add to the column recipe_code the relatio to the table recipe
        tbl.column('recipe_code').relation('alfa.recipe.code', mode='foreignkey')
        self.checkChanges('ALTER TABLE "alfa"."alfa_recipe_row" \nADD CONSTRAINT "fk_04a64b2e" FOREIGN KEY ("recipe_code") REFERENCES "alfa"."alfa_recipe" ("code") ON UPDATE CASCADE;')
    
    def test_06b_add_relation_to_pk_multi(self):
        #prendo la compositecolumn recipe_row_ref) e a
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_annotation')
        tbl.column('recipe_row_reference').relation(
            'alfa.recipe_row.composite_key',mode='foreignkey'
        )
        check_changes = 'CREATE INDEX idx_3e9365a8 ON "alfa"."alfa_recipe_row_annotation" USING btree (recipe_code, recipe_line);\nALTER TABLE "alfa"."alfa_recipe_row_annotation"\n ADD CONSTRAINT "fk_cbe2056f" FOREIGN KEY ("recipe_code", "recipe_line") REFERENCES "alfa"."alfa_recipe_row" ("recipe_code", "recipe_line") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_06c_add_relation_to_nopk_single(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('author_name',size=':44').relation('alfa.author.name', 
                                                      mode='foreignkey')
        check_changes = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "author_name" character varying(44) ;\nCREATE INDEX idx_44a37a95 ON "alfa"."alfa_recipe" USING btree (author_name);\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_7f18eae7" FOREIGN KEY ("author_name") REFERENCES "alfa"."alfa_author" ("name") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_06d_add_relation_to_nopk_multi(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('restaurant_vat',size=':30')
        tbl.column('restaurant_country',size='2')

        tbl.compositeColumn('restaurant_ref',columns='restaurant_country,restaurant_vat'
                            ).relation('alfa.restaurant.international_vat', mode='foreignkey')
        check_changes = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "restaurant_vat" character varying(30) ,\nADD COLUMN "restaurant_country" character(2) ;\nCREATE INDEX idx_f7e554d6 ON "alfa"."alfa_recipe" USING btree (restaurant_country, restaurant_vat);\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_8e2e04f3" FOREIGN KEY ("restaurant_country", "restaurant_vat") REFERENCES "alfa"."alfa_restaurant" ("country", "vat_number") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)


    def test_06e_add_relation_to_pk_single_onDelete_setnull_deferred(self):
        """
        Tests adding a foreign key constraint to a column.
        
        If the foreign key references a non-primary key field, an index
        should be automatically added to the referenced field to improve
        performance.
        """
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        # add to the column recipe_code the relatio to the table recipe
        tbl.column('company_code').relation('alfa.company.code', mode='foreignkey',onDelete_sql='setnull')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "company_code" text ;\nCREATE INDEX idx_6cbb7b70 ON "alfa"."alfa_recipe" USING btree (company_code);\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_f87f3ff6" FOREIGN KEY ("company_code") REFERENCES "alfa"."alfa_company" ("code") ON DELETE SET NULL ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;'
        self.checkChanges(check_value)
    

    def test_07a_create_table_with_relation_to_pk_single(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('product', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('description')
        tbl.column('recipe_code').relation('alfa.recipe.code',mode='foreignkey')
        check_value = 'CREATE TABLE "alfa"."alfa_product"(\n "id" serial8 NOT NULL,\n "description" text,\n "recipe_code" text,\n PRIMARY KEY (id)\n);\nCREATE INDEX idx_78fd5e36 ON "alfa"."alfa_product" USING btree (recipe_code);\nALTER TABLE "alfa"."alfa_product"\n ADD CONSTRAINT "fk_ff154564" FOREIGN KEY ("recipe_code") REFERENCES "alfa"."alfa_recipe" ("code") ON UPDATE CASCADE;'
        self.checkChanges(check_value)

    def test_07b_create_table_with_relation_to_pk_multi(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_alternative', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('description')
        tbl.column('vegan',dtype='B')
        tbl.column('gluten_free',dtype='B')
        tbl.column('recipe_code', size=':12').relation('alfa.recipe.code',mode='foreignkey')
        tbl.column('recipe_line',dtype='L')
        tbl.compositeColumn('recipe_row_reference',columns='recipe_code,recipe_line').relation(
            'alfa.recipe_row.composite_key',mode='foreignkey'
        )
        check_changes = 'CREATE TABLE "alfa"."alfa_recipe_row_alternative"(\n "id" serial8 NOT NULL,\n "description" text,\n "vegan" boolean,\n "gluten_free" boolean,\n "recipe_code" character varying(12),\n "recipe_line" bigint,\n PRIMARY KEY (id)\n);\nCREATE INDEX idx_17fca263 ON "alfa"."alfa_recipe_row_alternative" USING btree (recipe_code);\nCREATE INDEX idx_bd86c8b3 ON "alfa"."alfa_recipe_row_alternative" USING btree (recipe_code, recipe_line);\nALTER TABLE "alfa"."alfa_recipe_row_alternative"\n ADD CONSTRAINT "fk_a2e10c8f" FOREIGN KEY ("recipe_code") REFERENCES "alfa"."alfa_recipe" ("code") ON UPDATE CASCADE;\nALTER TABLE "alfa"."alfa_recipe_row_alternative"\n ADD CONSTRAINT "fk_b03ef3c2" FOREIGN KEY ("recipe_code", "recipe_line") REFERENCES "alfa"."alfa_recipe_row" ("recipe_code", "recipe_line") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_08a_modify_column_type(self):
        """Tests modifying the data type of an existing column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        tbl.column('description', dtype='varchar', size=':50')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" \n ALTER COLUMN "description" TYPE character varying(50);'
        self.checkChanges(check_value)

    def test_08b_modify_column_type(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_alternative')
        tbl.column('vegan',size='1',values='Y:Yes,C:Crudist,F:Fresh Fruit')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe_row_alternative" \n ALTER COLUMN "vegan" TYPE character(1);'
        self.checkChanges(check_value)

    def test_08c_modify_column_add_unique(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('author')
        tbl.column('tax_code',unique=True)
        tbl.column('foo') #columns added for testing the right placement of ADD constraint
        check_value = 'ALTER TABLE "alfa"."alfa_author"\nADD COLUMN "foo" text ;\nALTER TABLE "alfa"."alfa_author"\nADD CONSTRAINT "cst_99206169" UNIQUE ("tax_code");\nCREATE UNIQUE INDEX idx_fbdb510e ON "alfa"."alfa_author" USING btree (tax_code);'
        self.checkChanges(check_value)

    def test_08c_modify_column_remove_unique(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('author')
        tbl.column('tax_code',unique=False)
        check_value = 'ALTER TABLE "alfa"."alfa_author"\nDROP CONSTRAINT IF EXISTS "cst_99206169";'
        self.checkChanges(check_value)

    def test_09a_remove_column(self):
        pkg = self.src.package('alfa')
        pkg.table('author')['columns'].pop('foo')
        check_value = 'ALTER TABLE "alfa"."alfa_author" \n DROP COLUMN "foo";'
        self.checkChanges(check_value)

    def test_09b_remove_relation(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_alternative', pkey='id')
        col = tbl.column('recipe_code')
        col.pop('relation')
        check_value = '?'
        self.checkChanges(check_value)


@pytest.mark.skipif(gnrpostgres.SqlDbAdapter.not_capable(Capabilities.MIGRATIONS),
                    reason="Adapter doesn't support migrations")
class TestGnrSqlMigration_postgres(BaseGnrSqlMigration):
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

@pytest.mark.skipif(gnrpostgres3.SqlDbAdapter.not_capable(Capabilities.MIGRATIONS),
                    reason="Adapter doesn't support migrations")
class TestGnrSqlMigration_postgres3(BaseGnrSqlMigration):
    @classmethod
    def init(cls):
        """
        Initializes the test database connection with PostgreSQL settings.
        """
        cls.name = 'postgres3'
        cls.dbname = 'test_gnrsqlmigration'
        cls.db = GnrSqlDb(
            implementation='postgres3',
            host=cls.pg_conf.get("host"),
            port=cls.pg_conf.get("port"),
            dbname=cls.dbname,
            user=cls.pg_conf.get("user"),
            password=cls.pg_conf.get("password")
        )


class ToDo:
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
