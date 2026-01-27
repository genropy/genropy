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
            changes = self.migrator.getChanges()
            self.migrator.applyChanges()
            return changes
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

        check_value = 'ALTER TABLE "alfa"."alfa_recipe" \n ADD COLUMN "ins_ts" timestamp without time zone ,\nADD COLUMN "recipy_type" character varying(2) ;\nCREATE INDEX idx_f473bae1 ON "alfa"."alfa_recipe" USING btree ("ins_ts") ;\nCREATE INDEX idx_490f54d9 ON "alfa"."alfa_recipe" USING btree ("recipy_type") ;'
        self.checkChanges(check_value)

    def test_04c_add_unique_multiple_constraint(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('restaurant', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('name',size=':45')
        tbl.column('country',size='2')
        tbl.column('vat_number',size=':30')
        tbl.compositeColumn('international_vat',columns='country,vat_number',unique=True)
        check_value = 'CREATE TABLE "alfa"."alfa_restaurant"(\n "id" serial8 NOT NULL,\n "name" character varying(45),\n "country" character(2),\n "vat_number" character varying(30),\n PRIMARY KEY (id),\n CONSTRAINT "cst_703bf76b" UNIQUE ("country", "vat_number")\n);'
        self.checkChanges(check_value)


    def test_04d_add_unique_column(self):
        """Tests adding a new column to an existing table."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('testuniquecol',unique=True,size=':10')
        check_value = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "testuniquecol" character varying(10);\nALTER TABLE "alfa"."alfa_recipe"\nADD CONSTRAINT "cst_f797d32c" UNIQUE ("testuniquecol");'
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

    def test_05d_create_table_with_pkey_explicit_unique(self):
        """Tests creating a table with a primary key column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('company', pkey='code')
        tbl.column('code', size=':30',unique=True)
        tbl.column('description')
        check_value = 'CREATE TABLE "alfa"."alfa_company"(\n "code" character varying(30) NOT NULL,\n "description" text,\n PRIMARY KEY (code)\n);'
        self.checkChanges(check_value)

    def test_05e_create_table_with_pkey_and_unique_col(self):
        """Tests creating a table with a primary key column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('test_table_with_uniquecol', pkey='code')
        tbl.column('code', size=':30',unique=True)
        tbl.column('description')
        tbl.column('uniquecol',unique=True,size='10')
        check_value = 'CREATE TABLE "alfa"."alfa_test_table_with_uniquecol"(\n "code" character varying(30) NOT NULL,\n "description" text,\n "uniquecol" character(10),\n PRIMARY KEY (code)\n);\nALTER TABLE "alfa"."alfa_test_table_with_uniquecol"\nADD CONSTRAINT "cst_9bbd2120" UNIQUE ("uniquecol");'
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
        check_changes = 'CREATE INDEX idx_3e9365a8 ON "alfa"."alfa_recipe_row_annotation" USING btree ("recipe_code", "recipe_line");\nALTER TABLE "alfa"."alfa_recipe_row_annotation"\n ADD CONSTRAINT "fk_cbe2056f" FOREIGN KEY ("recipe_code", "recipe_line") REFERENCES "alfa"."alfa_recipe_row" ("recipe_code", "recipe_line") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_06c_add_relation_to_nopk_single(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('author_name',size=':44').relation('alfa.author.name', 
                                                      mode='foreignkey')
        check_changes = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "author_name" character varying(44) ;\nCREATE INDEX idx_44a37a95 ON "alfa"."alfa_recipe" USING btree ("author_name");\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_7f18eae7" FOREIGN KEY ("author_name") REFERENCES "alfa"."alfa_author" ("name") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_06d_add_relation_to_nopk_multi(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe')
        tbl.column('restaurant_vat',size=':30')
        tbl.column('restaurant_country',size='2')

        tbl.compositeColumn('restaurant_ref',columns='restaurant_country,restaurant_vat'
                            ).relation('alfa.restaurant.international_vat', mode='foreignkey')
        check_changes = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "restaurant_vat" character varying(30) ,\nADD COLUMN "restaurant_country" character(2) ;\nCREATE INDEX idx_f7e554d6 ON "alfa"."alfa_recipe" USING btree ("restaurant_country", "restaurant_vat");\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_8e2e04f3" FOREIGN KEY ("restaurant_country", "restaurant_vat") REFERENCES "alfa"."alfa_restaurant" ("country", "vat_number") ON UPDATE CASCADE;'
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
        check_value = 'ALTER TABLE "alfa"."alfa_recipe"\nADD COLUMN "company_code" text ;\nCREATE INDEX idx_6cbb7b70 ON "alfa"."alfa_recipe" USING btree ("company_code");\nALTER TABLE "alfa"."alfa_recipe"\n ADD CONSTRAINT "fk_f87f3ff6" FOREIGN KEY ("company_code") REFERENCES "alfa"."alfa_company" ("code") ON DELETE SET NULL ON UPDATE CASCADE DEFERRABLE INITIALLY DEFERRED;'
        self.checkChanges(check_value)
    

    def test_07a_create_table_with_relation_to_pk_single(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('product', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('description')
        tbl.column('recipe_code').relation('alfa.recipe.code',mode='foreignkey')
        check_value = 'CREATE TABLE "alfa"."alfa_product"(\n "id" serial8 NOT NULL,\n "description" text,\n "recipe_code" text,\n PRIMARY KEY (id)\n);\nCREATE INDEX idx_78fd5e36 ON "alfa"."alfa_product" USING btree ("recipe_code");\nALTER TABLE "alfa"."alfa_product"\n ADD CONSTRAINT "fk_ff154564" FOREIGN KEY ("recipe_code") REFERENCES "alfa"."alfa_recipe" ("code") ON UPDATE CASCADE;'
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
        check_changes = 'CREATE TABLE "alfa"."alfa_recipe_row_alternative"(\n "id" serial8 NOT NULL,\n "description" text,\n "vegan" boolean,\n "gluten_free" boolean,\n "recipe_code" character varying(12),\n "recipe_line" bigint,\n PRIMARY KEY (id)\n);\nCREATE INDEX idx_17fca263 ON "alfa"."alfa_recipe_row_alternative" USING btree ("recipe_code");\nCREATE INDEX idx_bd86c8b3 ON "alfa"."alfa_recipe_row_alternative" USING btree ("recipe_code", "recipe_line");\nALTER TABLE "alfa"."alfa_recipe_row_alternative"\n ADD CONSTRAINT "fk_a2e10c8f" FOREIGN KEY ("recipe_code") REFERENCES "alfa"."alfa_recipe" ("code") ON UPDATE CASCADE;\nALTER TABLE "alfa"."alfa_recipe_row_alternative"\n ADD CONSTRAINT "fk_b03ef3c2" FOREIGN KEY ("recipe_code", "recipe_line") REFERENCES "alfa"."alfa_recipe_row" ("recipe_code", "recipe_line") ON UPDATE CASCADE;'
        self.checkChanges(check_changes)

    def test_08a_modify_column_type(self):
        """Tests modifying the data type of an existing column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        tbl.column('description', size=':50')
        check_value = 'ALTER TABLE "alfa"."alfa_ingredient" \n ALTER COLUMN "description" TYPE character varying(50);'
        self.checkChanges(check_value)


    def test_08e_modify_column_from_text_to_bytea(self):
        """Tests modifying the data type of an existing column."""
        pkg = self.src.package('alfa')
        tbl = pkg.table('ingredient')
        foo_varchar = tbl.column('foo_varchar', size=':50')
        self.checkChanges(apply_only=True)
        foo_varchar.attributes['dtype'] = 'O'
        foo_varchar.attributes.pop('size')
        self.checkChanges('ALTER TABLE "alfa"."alfa_ingredient"\nDROP COLUMN "foo_varchar",\nADD COLUMN "foo_varchar" bytea;')



    def test_08b_modify_column_type(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('recipe_row_alternative')
        tbl.column('vegan').attributes.pop('dtype')
        tbl.column('vegan',size='1',values='Y:Yes,C:Crudist,F:Fresh Fruit')
        # Now uses simple ALTER COLUMN TYPE (any type → text is always convertible)
        check_value = 'ALTER TABLE "alfa"."alfa_recipe_row_alternative"\nALTER COLUMN "vegan" TYPE character(1);'
        self.checkChanges(check_value)

    def test_08c_modify_column_add_unique(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('author')
        tbl.column('tax_code',unique=True)
        tbl.column('foo') #columns added for testing the right placement of ADD constraint
        check_value = 'ALTER TABLE "alfa"."alfa_author"\nADD COLUMN "foo" text ;\nALTER TABLE "alfa"."alfa_author"\nADD CONSTRAINT "cst_99206169" UNIQUE ("tax_code");'
        self.checkChanges(check_value)

    def test_08c_modify_column_remove_unique(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('author')
        tbl.column('tax_code').attributes.pop('unique')
        check_value = 'ALTER TABLE "alfa"."alfa_author"\nDROP CONSTRAINT IF EXISTS "cst_99206169";'
        self.checkChanges(check_value)  

    def test_08d_modify_dtype_bis(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('author')
        tbl.column('foo',dtype='D')
        # Prudent mode: direct conversion with USING clause (no backup)
        check_value = 'ALTER TABLE "alfa"."alfa_author"\nALTER COLUMN "foo" TYPE date USING CASE WHEN "foo" IS NULL THEN NULL WHEN "foo" ~ \'^[0-9]{4}-[0-9]{2}-[0-9]{2}\' THEN "foo"::date ELSE NULL END;'
        self.checkChanges(check_value)

    def test_09a_remove_column(self):
        pkg = self.src.package('alfa')
        pkg.table('author')['columns'].pop('foo')
        check_value = 'ALTER TABLE "alfa"."alfa_author" \n DROP COLUMN "foo";'
        self.checkChanges(check_value)


    def test_10a_empty_table_creation(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('my_empty_table')
        self.checkChanges(apply_only=True)
        tbl.attributes.update(pkey='id')
        tbl.column('id',size='22')
        self.checkChanges('CREATE TABLE "alfa"."alfa_my_empty_table"(\n "id" character(22) NOT NULL,\n PRIMARY KEY (id)\n);')

    def test_11_varchar_min_max(self):
        pkg = self.src.package('alfa')
        tbl = pkg.table('text_test_table', pkey='id')
        tbl.column('id', dtype='serial')

        # please see #324 - varchar colums with min/max should only
        # use the max to define the column size attribute
        tbl.column('code', dtype='A', size="5:18")
        check_value = 'CREATE TABLE "alfa"."alfa_text_test_table"("id" serial8 NOT NULL, "code" character varying(18), PRIMARY KEY(id));'
        self.checkChanges(check_value)

    def test_12a_simple_text_conversion(self):
        """Test simple type conversion without USING clause (T → A)"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col')  # Text column (no size = text)
        check_value = 'CREATE TABLE "alfa"."alfa_type_conv_test"("id" serial8 NOT NULL, "text_col" text, PRIMARY KEY(id));'
        self.checkChanges(check_value)

        # Now change text to varchar (simple conversion)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', size=':50')  # Changed to varchar(50)
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "text_col" TYPE character varying(50);'
        self.checkChanges(check_value)

    def test_12b_simple_text_to_varchar(self):
        """Test simple conversion back (A → A with different size)"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')  # Change back to varchar with different size
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "text_col" TYPE character varying(30);'
        self.checkChanges(check_value)

    def test_12c_text_to_timestamp_conversion(self):
        """Test complex conversion with USING clause (T → DHZ) - prudent mode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "ts_col" text;', apply_only=True)

        # Change to timestamp with timezone (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "ts_col" TYPE timestamp with time zone USING CASE WHEN "ts_col" IS NULL THEN NULL WHEN "ts_col" ~ \'^[0-9]{4}-[0-9]{2}-[0-9]{2}\' THEN "ts_col"::timestamp with time zone ELSE NULL END;'
        self.checkChanges(check_value)

    def test_12d_text_to_date_conversion(self):
        """Test text to date conversion - prudent mode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "date_col" text;', apply_only=True)

        # Change to date (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "date_col" TYPE date USING CASE WHEN "date_col" IS NULL THEN NULL WHEN "date_col" ~ \'^[0-9]{4}-[0-9]{2}-[0-9]{2}\' THEN "date_col"::date ELSE NULL END;'
        self.checkChanges(check_value)

    def test_12e_text_to_integer_conversion(self):
        """Test text to integer conversion - prudent mode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "int_col" text;', apply_only=True)

        # Change to integer (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "int_col" TYPE integer USING CASE WHEN "int_col" IS NULL THEN NULL WHEN "int_col" ~ \'^-?[0-9]+$\' THEN "int_col"::integer ELSE NULL END;'
        self.checkChanges(check_value)

    def test_12f_text_to_boolean_conversion(self):
        """Test text to boolean conversion with backup"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "bool_col" text;', apply_only=True)

        # Change to boolean (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "bool_col" TYPE boolean USING CASE WHEN "bool_col" IS NULL THEN NULL WHEN LOWER("bool_col") IN (\'true\', \'t\', \'yes\', \'y\', \'1\') THEN TRUE WHEN LOWER("bool_col") IN (\'false\', \'f\', \'no\', \'n\', \'0\', \'\') THEN FALSE ELSE NULL END;'
        self.checkChanges(check_value)

    def test_12g_text_to_numeric_conversion(self):
        """Test text to numeric conversion - prudent mode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "num_col" text;', apply_only=True)

        # Change to numeric (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "num_col" TYPE numeric(10,2) USING CASE WHEN "num_col" IS NULL THEN NULL WHEN "num_col" ~ \'^-?[0-9]+(\\.[0-9]+)?$\' THEN "num_col"::numeric ELSE NULL END;'
        self.checkChanges(check_value)

    def test_12h_real_to_integer_conversion(self):
        """Test real to integer conversion with rounding - prudent mode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='R')
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "real_col" real;', apply_only=True)

        # Change to integer with ROUND (prudent mode: no backup)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "real_col" TYPE integer USING CASE WHEN "real_col" IS NULL THEN NULL ELSE ROUND("real_col")::integer END;'
        self.checkChanges(check_value)

    def test_12i_incompatible_conversion_empty_column(self):
        """Test incompatible conversion on empty column (should drop and recreate)"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col')  # Add text column
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "bytea_col" text;', apply_only=True)

        # Change to bytea (incompatible, should drop and recreate)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test"\nDROP COLUMN "bytea_col",\nADD COLUMN "bytea_col" bytea;'
        self.checkChanges(check_value)

    def test_12j_date_conversions(self):
        """Test date/time type conversions"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='D')  # Start with date
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "date_time_col" date;', apply_only=True)

        # Convert to timestamp (simple conversion)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='DH')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "date_time_col" TYPE timestamp without time zone;'
        self.checkChanges(check_value, apply_only=True)

        # Convert to timestamp with timezone (simple conversion)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='DHZ')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "date_time_col" TYPE timestamp with time zone;'
        self.checkChanges(check_value)

    def test_12k_numeric_conversions(self):
        """Test numeric type conversions"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='DHZ')
        tbl.column('numeric_col', dtype='I')  # Start with integer
        self.checkChanges('ALTER TABLE "alfa"."alfa_type_conv_test" \n ADD COLUMN "numeric_col" integer;', apply_only=True)

        # Convert to bigint (simple conversion)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='DHZ')
        tbl.column('numeric_col', dtype='L')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "numeric_col" TYPE bigint;'
        self.checkChanges(check_value, apply_only=True)

        # Convert to numeric (simple conversion)
        pkg = self.src.package('alfa')
        tbl = pkg.table('type_conv_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='A', size=':30')
        tbl.column('ts_col', dtype='DHZ')
        tbl.column('date_col', dtype='D')
        tbl.column('int_col', dtype='I')
        tbl.column('bool_col', dtype='B')
        tbl.column('num_col', dtype='N', size='10,2')
        tbl.column('real_col', dtype='I')
        tbl.column('bytea_col', dtype='O')
        tbl.column('date_time_col', dtype='DHZ')
        tbl.column('numeric_col', dtype='N', size='14,2')
        check_value = 'ALTER TABLE "alfa"."alfa_type_conv_test" \n ALTER COLUMN "numeric_col" TYPE numeric(14,2);'
        self.checkChanges(check_value)

    def test_12l_any_to_text_integer(self):
        """Test generic conversion: integer to text"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='I')
        self.checkChanges('CREATE TABLE "alfa"."alfa_to_text_test"("id" serial8 NOT NULL, "int_col" integer, PRIMARY KEY(id));', apply_only=True)

        # Convert integer to text
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        check_value = 'ALTER TABLE "alfa"."alfa_to_text_test" \n ALTER COLUMN "int_col" TYPE text;'
        self.checkChanges(check_value)

    def test_12m_any_to_text_date(self):
        """Test generic conversion: date to text"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='D')
        self.checkChanges('ALTER TABLE "alfa"."alfa_to_text_test" \n ADD COLUMN "date_col" date;', apply_only=True)

        # Convert date to text
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        check_value = 'ALTER TABLE "alfa"."alfa_to_text_test" \n ALTER COLUMN "date_col" TYPE text;'
        self.checkChanges(check_value)

    def test_12n_any_to_text_boolean(self):
        """Test generic conversion: boolean to text"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='B')
        self.checkChanges('ALTER TABLE "alfa"."alfa_to_text_test" \n ADD COLUMN "bool_col" boolean;', apply_only=True)

        # Convert boolean to text
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        check_value = 'ALTER TABLE "alfa"."alfa_to_text_test" \n ALTER COLUMN "bool_col" TYPE text;'
        self.checkChanges(check_value)

    def test_12o_any_to_text_timestamp(self):
        """Test generic conversion: timestamp with timezone to text"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='DHZ')
        self.checkChanges('ALTER TABLE "alfa"."alfa_to_text_test" \n ADD COLUMN "ts_col" timestamp with time zone;', apply_only=True)

        # Convert timestamp to text
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='T')
        check_value = 'ALTER TABLE "alfa"."alfa_to_text_test" \n ALTER COLUMN "ts_col" TYPE text;'
        self.checkChanges(check_value)

    def test_12p_any_to_text_numeric(self):
        """Test generic conversion: numeric to varchar"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='T')
        tbl.column('num_col', dtype='N', size='10,2')
        self.checkChanges('ALTER TABLE "alfa"."alfa_to_text_test" \n ADD COLUMN "num_col" numeric(10,2);', apply_only=True)

        # Convert numeric to varchar
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='T')
        tbl.column('num_col', dtype='A', size=':50')
        check_value = 'ALTER TABLE "alfa"."alfa_to_text_test" \n ALTER COLUMN "num_col" TYPE character varying(50);'
        self.checkChanges(check_value)

    def test_12q_bytea_to_text(self):
        """Test bytea to text conversion with encode"""
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='T')
        tbl.column('num_col', dtype='A', size=':50')
        tbl.column('bytea_col', dtype='O')
        self.checkChanges('ALTER TABLE "alfa"."alfa_to_text_test" \n ADD COLUMN "bytea_col" bytea;', apply_only=True)

        # Convert bytea to text (requires encode)
        pkg = self.src.package('alfa')
        tbl = pkg.table('to_text_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('int_col', dtype='T')
        tbl.column('date_col', dtype='T')
        tbl.column('bool_col', dtype='T')
        tbl.column('ts_col', dtype='T')
        tbl.column('num_col', dtype='A', size=':50')
        tbl.column('bytea_col', dtype='T')
        check_value = "ALTER TABLE \"alfa\".\"alfa_to_text_test\" \n ALTER COLUMN \"bytea_col\" TYPE text USING encode(\"bytea_col\", 'hex');"
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


class BaseGnrSqlMigration_ForceMode(BaseGnrSqlTest):
    """
    Test suite for SQL migration force mode with backup columns.
    In force mode, type conversions create backup columns to preserve original data.
    """

    @classmethod
    def setup_class(cls):
        """
        Sets up the test class with force=True migrator.
        """
        super().setup_class()
        cls.init()
        cls.src = cls.db.model.src
        cls.migrator = SqlMigrator(cls.db, removeDisabled=False, force=True)
        cls.db.dropDb(cls.dbname)

    def checkChanges(self, expected_value=None, apply_only=False, skip_recheck=False):
        """
        Validates the expected SQL changes against actual changes.

        For force mode tests with backup columns, set skip_recheck=True because
        after applying, the backup columns exist in DB but not in ORM, so the
        migrator will always want to drop them (which is expected behavior).
        """
        self.db.startup()
        self.migrator.prepareMigrationCommands()
        if apply_only:
            changes = self.migrator.getChanges()
            self.migrator.applyChanges()
            return changes
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
            if not skip_recheck:
                self.migrator.prepareMigrationCommands()
                changes = self.migrator.getChanges()
                if changes:
                    print('unexpected changes', changes)
                assert not changes, 'Failed to execute SQL command as expected.'

    def test_force_01_create_db(self):
        """Tests database creation (same as prudent mode)"""
        check_value = """CREATE DATABASE "test_gnrsqlmigration_force" ENCODING 'UNICODE';\n"""
        self.checkChanges(check_value)

    def test_force_02_create_schema_and_table(self):
        """Creates schema and test table for force mode tests"""
        self.src.package('beta', sqlschema='beta')
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col')
        self.checkChanges(apply_only=True)

    def test_force_03_text_to_date_with_backup(self):
        """Test text to date conversion with backup column in force mode"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        # In force mode: creates backup column, copies data, then converts
        check_value = '''ALTER TABLE "beta"."beta_force_test" ADD COLUMN "text_col__T" text;
UPDATE "beta"."beta_force_test" SET "text_col__T" = "text_col"::text;
ALTER TABLE "beta"."beta_force_test"
ALTER COLUMN "text_col" TYPE date USING CASE WHEN "text_col" IS NULL THEN NULL WHEN "text_col" ~ \'^[0-9]{4}-[0-9]{2}-[0-9]{2}\' THEN "text_col"::date ELSE NULL END;'''
        # skip_recheck because backup columns are intentionally not in ORM
        self.checkChanges(check_value, skip_recheck=True)

    def test_force_04_add_integer_col(self):
        """Add integer column for next conversion test"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source')
        self.checkChanges(apply_only=True)

    def test_force_05_text_to_integer_with_backup(self):
        """Test text to integer conversion with backup column"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source', dtype='I')
        check_value = '''ALTER TABLE "beta"."beta_force_test" ADD COLUMN "int_source__T" text;
UPDATE "beta"."beta_force_test" SET "int_source__T" = "int_source"::text;
ALTER TABLE "beta"."beta_force_test"
ALTER COLUMN "int_source" TYPE integer USING CASE WHEN "int_source" IS NULL THEN NULL WHEN "int_source" ~ \'^-?[0-9]+$\' THEN "int_source"::integer ELSE NULL END;'''
        # skip_recheck because backup columns are intentionally not in ORM
        self.checkChanges(check_value, skip_recheck=True)

    def test_force_06_add_boolean_col(self):
        """Add text column for boolean conversion test"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source', dtype='I')
        tbl.column('bool_source')
        self.checkChanges(apply_only=True)

    def test_force_07_text_to_boolean_with_backup(self):
        """Test text to boolean conversion with backup column"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source', dtype='I')
        tbl.column('bool_source', dtype='B')
        check_value = '''ALTER TABLE "beta"."beta_force_test" ADD COLUMN "bool_source__T" text;
UPDATE "beta"."beta_force_test" SET "bool_source__T" = "bool_source"::text;
ALTER TABLE "beta"."beta_force_test"
ALTER COLUMN "bool_source" TYPE boolean USING CASE WHEN "bool_source" IS NULL THEN NULL WHEN LOWER("bool_source") IN (\'true\', \'t\', \'yes\', \'y\', \'1\') THEN TRUE WHEN LOWER("bool_source") IN (\'false\', \'f\', \'no\', \'n\', \'0\', \'\') THEN FALSE ELSE NULL END;'''
        # skip_recheck because backup columns are intentionally not in ORM
        self.checkChanges(check_value, skip_recheck=True)

    def test_force_08_any_to_text_no_backup(self):
        """Test any-to-text conversion has no backup (simple conversion)"""
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source', dtype='I')
        tbl.column('bool_source', dtype='B')
        tbl.column('numeric_col', dtype='N', size='10,2')
        self.checkChanges(apply_only=True)

        # Convert numeric to text - no backup needed (lossless conversion)
        pkg = self.src.package('beta')
        tbl = pkg.table('force_test', pkey='id')
        tbl.column('id', dtype='serial')
        tbl.column('text_col', dtype='D')
        tbl.column('int_source', dtype='I')
        tbl.column('bool_source', dtype='B')
        # Change numeric_col to text (remove size attribute to get text, not char)
        numeric_col = tbl.column('numeric_col', dtype='T')
        numeric_col.attributes.pop('size', None)
        # Simple ALTER TYPE, no backup column
        check_value = 'ALTER TABLE "beta"."beta_force_test" \n ALTER COLUMN "numeric_col" TYPE text;'
        # skip_recheck because backup columns from previous tests are still in DB
        self.checkChanges(check_value, skip_recheck=True)


@pytest.mark.skipif(gnrpostgres.SqlDbAdapter.not_capable(Capabilities.MIGRATIONS),
                    reason="Adapter doesn't support migrations")
class TestGnrSqlMigration_postgres_force(BaseGnrSqlMigration_ForceMode):
    @classmethod
    def init(cls):
        """
        Initializes the test database connection with PostgreSQL settings (force mode).
        """
        cls.name = 'postgres_force'
        cls.dbname = 'test_gnrsqlmigration_force'
        cls.db = GnrSqlDb(
            implementation='postgres',
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



    def test_10b_change_pkey(self):
        """Not implemented feature"""
        pass


