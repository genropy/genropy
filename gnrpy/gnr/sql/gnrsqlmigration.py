import re

import json
import time
import functools
from deepdiff import DeepDiff

COL_JSON_KEYS = ("dtype","notnull","default","size")


def compare_json(json1, json2):
    """Compara due strutture JSON e ritorna le differenze."""
    diff = DeepDiff(json1, json2, ignore_order=True)
    return diff


def json_equal(json1, json2):
    """Confronta due JSON indipendentemente dall'ordine degli elementi."""
    json1_str = json.dumps(json1, sort_keys=True)
    json2_str = json.dumps(json2, sort_keys=True)
    return json1_str == json2_str



def measure_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        print(f"Execution time of {func.__name__}: {duration:.4f} seconds")
        return result
    return wrapper


from webob import year

class OrmExtractor:
    col_json_keys =  COL_JSON_KEYS

    def __init__(self, db):
        self.db = db
        self.json_structure = {}

    def fill_json_package(self,pkgobj):
        self.json_structure[pkgobj.sqlname] = {
            'metadata':{},
            'tables':{}
        }
        for tblobj in pkgobj.tables.values():
            self.fill_json_table(tblobj)

    def fill_json_table(self,tblobj):
        schema_name = tblobj.pkg.sqlname
        self.json_structure[schema_name]['tables'][tblobj.sqlname] = {
            "metadata": {},
            "columns": {},
            "constraints": {},
            "indices": {}
        }
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj)

    def fill_json_column(self,colobj):
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        self.json_structure[schema_name]['tables'][table_name]['columns'][colobj.sqlname] = self.convert_colattr(colobj)

    def convert_colattr(self,colobj):
        return {k:v for k,v in colobj.attributes.items() if k in self.col_json_keys and v is not None}
    

    def get_json_struct(self):
        """Generates the JSON structure of the database."""
        for pkg in self.db.packages.values():
            self.fill_json_package(pkg)
        return self.json_structure
    
class DatabaseMetadataExtractor(object):
    col_json_keys =  COL_JSON_KEYS
    
    def __init__(self, db):
        self.db = db
        self.conn = None
        self.schemas = [pkg.sqlname for pkg in self.db.packages.values()]


    def connect(self):
        """Establishes the connection to the database."""
        self.conn = self.db.adapter.connect()

    def close_connection(self):
        """Closes the connection to the database."""
        if self.conn:
            self.conn.close()

    def fetch_all_metadata(self):
        """Fetches schemas, tables, and columns in one query."""

        schema_list =  str(tuple(self.schemas))
        query = f"""
            SELECT
                s.schema_name,
                t.table_name,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default
            FROM
                information_schema.schemata s
            JOIN
                information_schema.tables t
                ON s.schema_name = t.table_schema
            JOIN
                information_schema.columns c
                ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE
                s.schema_name IN {schema_list}
            ORDER BY
                s.schema_name, t.table_name, c.ordinal_position;
        """
        
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def fetch_constraints_and_indices(self):
        """Fetches all constraints and indices for tables."""
        schema_list =  str(tuple(self.schemas))
        query = f"""
            SELECT
                i.schemaname AS table_schema,
                i.tablename AS table_name,
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                ccu.table_schema AS referenced_table_schema,
                ccu.table_name AS referenced_table_name,
                ccu.column_name AS referenced_column_name,
                i.indexname,
                i.indexdef
            FROM
                pg_indexes i
            LEFT JOIN
                information_schema.table_constraints tc
                ON i.schemaname = tc.table_schema
                AND i.tablename = tc.table_name
            LEFT JOIN
                information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            LEFT JOIN
                information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE
                i.schemaname IN {schema_list}
            ORDER BY
                i.schemaname, i.tablename, tc.constraint_name;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


    def parse_index_definition(self,index_def):
        """Parses the index definition into components."""
        index_info = {}
        
        index_info['unique'] = 'UNIQUE' in index_def

        match = re.search(r'USING (\w+)', index_def)
        if match:
            index_info['index_type'] = match.group(1)
        else:
            index_info['index_type'] = 'btree'  # Default 

        match = re.search(r'\(([^)]+)\)', index_def)
        if match:
            index_info['columns'] = match.group(1).split(', ')
        
        return index_info

    def process_constraints_and_indices(self, db_structure, constraints_and_indices):
        """Processes constraints and indices data."""
        for (schema_name, table_name, constraint_name, constraint_type, column_name, 
            referenced_table_schema, referenced_table_name, referenced_column_name, index_name, index_def) in constraints_and_indices:
            
            if constraint_type == 'check' and '_not_null' in constraint_name:
                continue  # Skip auto-generated NOT NULL constraints
    
            # Ensure the constraints dictionary exists
            if "constraints" not in db_structure[schema_name]["tables"][table_name]:
                db_structure[schema_name]["tables"][table_name]["constraints"] = {}

            # Only process constraint details if the constraint type is not None
            if constraint_type is not None:
                if constraint_name not in db_structure[schema_name]["tables"][table_name]["constraints"]:
                    db_structure[schema_name]["tables"][table_name]["constraints"][constraint_name] = {
                        "type": constraint_type.lower(),
                        "columns": []
                    }

                # Add the column to the constraint if it exists
                if column_name and column_name not in db_structure[schema_name]["tables"][table_name]["constraints"][constraint_name]["columns"]:
                    db_structure[schema_name]["tables"][table_name]["constraints"][constraint_name]["columns"].append(column_name)

                # Add the foreign key reference if applicable
                if constraint_type == 'FOREIGN KEY' and referenced_table_schema:
                    reference = f"{referenced_table_schema}.{referenced_table_name}({referenced_column_name})"
                    db_structure[schema_name]["tables"][table_name]["constraints"][constraint_name]["reference"] = reference

            # Ensure the indices dictionary exists
            if "indices" not in db_structure[schema_name]["tables"][table_name]:
                db_structure[schema_name]["tables"][table_name]["indices"] = {}

            # Parse the index definition and store relevant details
            if index_name:
                index_info = self.parse_index_definition(index_def)
                db_structure[schema_name]["tables"][table_name]["indices"][index_name] = {
                    "index_name": index_name,
                    "index_type": index_info.get("index_type", "btree"),
                    "unique": index_info.get("unique", False),
                    "columns": index_info.get("columns", []),
                    "definition": index_def  # Mantiene anche la definizione completa se serve
                }
                
    def metadataAdapter(self,metadata):
        for schema_name, table_name, column_name, data_type, char_max_length, is_nullable, column_default in metadata:
            yield dict(schema_name=schema_name,table_name=table_name,
                       name=column_name,
                       dtype = data_type,
                       length=char_max_length,
                        notnull= is_nullable,
                        default= column_default)
            
    def process_metadata(self, db_structure, metadata):
        """Processes schema, table, and column metadata."""
        for c in self.db.adapter.columnAdapter(self.metadataAdapter(metadata)):
            schema_name = c.pop('_pg_schema_name')
            table_name = c.pop('_pg_table_name')
            column_name = c.pop('name')
            colattr = {k:v for k,v in c.items()  if k in self.col_json_keys and v is not None}
            if colattr['notnull'] is False:
                colattr.pop('notnull')

            if schema_name not in db_structure:
                db_structure[schema_name] = {
                    "metadata": {},
                    "tables": {}
                }
            if table_name not in db_structure[schema_name]["tables"]:
                db_structure[schema_name]["tables"][table_name] = {
                    "metadata": {},
                    "columns": {},
                    "constraints": {},
                    "indices": {}
                }
            db_structure[schema_name]["tables"][table_name]["columns"][column_name] = colattr
    
    @measure_time
    def get_json_struct(self,metadata_only=False):
        """Generates the JSON structure of the database."""
        db_structure = {}
        self.connect()

        try:
            # Fetch all metadata and constraints/indices
            metadata = self.fetch_all_metadata()
            self.process_metadata(db_structure, metadata)

           #if not metadata_only:
           #    constraints_and_indices = self.fetch_constraints_and_indices()
           #    # Process metadata and constraints/indices
           #    self.process_constraints_and_indices(db_structure, constraints_and_indices)

        finally:
            self.close_connection()

        return db_structure

def ormStructure(db):
    extractor = OrmExtractor(db)
    return extractor.get_json_struct()


def sqlStructure(db):
    extractor = DatabaseMetadataExtractor(db)
    return extractor.get_json_struct(metadata_only=True)


if __name__ == '__main__':
    # Connection parameters
    from gnr.app.gnrapp import GnrApp
    db = GnrApp('mtx_tester').db    
    structure_sql = sqlStructure(db)
    with open('db_structure.json', 'w') as f:
        json.dump(structure_sql, f, indent=4)

    structure_orm = ormStructure(db)
    with open('orm_structure.json', 'w') as f:
        json.dump(structure_orm, f, indent=4)
    isEqual = json_equal(structure_sql,structure_orm)
    if not isEqual:
        diff = compare_json(structure_sql,structure_orm)
        print('diff',diff)