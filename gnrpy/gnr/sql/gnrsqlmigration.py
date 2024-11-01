import re

import json
import time
import functools
from collections import defaultdict
from deepdiff import DeepDiff, Delta
from gnr.app.gnrapp import GnrApp
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException,GnrSqlException

COL_JSON_KEYS = ("dtype","notnull","default","size","unique")


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


import jsmin
from webob import year

class OrmExtractor:
    col_json_keys =  COL_JSON_KEYS

    def __init__(self, db):
        self.db = db
        self.json_structure = {'root':{
            'schemas':{},
            'entity':'db',
            'entity_name':self.db.dbname
            }
        }
        self.schemas = self.json_structure['root']['schemas']

    def fill_json_package(self,pkgobj):
        self.schemas[pkgobj.sqlname] = {
            'metadata':{},
            'entity':'schema',
            'entity_name':pkgobj.sqlname,
            'tables':{}
        }
        for tblobj in pkgobj.tables.values():
            self.fill_json_table(tblobj)

    def fill_json_table(self,tblobj):
        schema_name = tblobj.pkg.sqlname
        pkeys = ','.join([tblobj.column(col).sqlname for col in tblobj.attributes['pkey'].split(',')])
        self.schemas[schema_name]['tables'][tblobj.sqlname] = {
            "metadata": {},
            'entity':'table',
            'schema_name':schema_name,
            'entity_name':tblobj.sqlname,
            "attributes":{"pkeys":pkeys},
            "columns": {},
            "constraints": {},
            "indices": {}
        }
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj)

    def fill_json_column(self,colobj):
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        self.schemas[schema_name]['tables'][table_name]['columns'][colobj.sqlname] = {"entity":"column",
                                                                                      "schema_name":schema_name,
                                                                                      "table_name":table_name,
                                                                                      "entity_name":colobj.sqlname,
                                                                                      "attributes":self.convert_colattr(colobj)}

    def convert_colattr(self,colobj):
        return {k:v for k,v in colobj.attributes.items() if k in self.col_json_keys and v is not None}
    

    def get_json_struct(self):
        """Generates the JSON structure of the database."""
        for pkg in self.db.packages.values():
            self.fill_json_package(pkg)
        return self.json_structure
    
class DbExtractor(object):
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

    def fetch_constraints_and_indices(self):
        """Fetches all constraints and indices for tables."""
        query = """
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
                i.schemaname IN %s
            ORDER BY
                i.schemaname, i.tablename, tc.constraint_name;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query,(tuple(self.schemas),))
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

    def get_foreign_keys(self):
        query = """
        SELECT 
            kcu.constraint_name AS constraint_name,
            kcu.constraint_schema AS schema_name,
            kcu.table_name AS table_name,
            kcu.column_name AS column_name,
            ccu.constraint_schema AS related_schema,
            ccu.table_name AS related_table,
            ccu.column_name AS related_column,
            rc.update_rule AS on_update,
            rc.delete_rule AS on_delete,
            tc.is_deferrable,
            tc.initially_deferred,
            kcu.ordinal_position
        FROM 
            information_schema.table_constraints AS tc
        JOIN 
            information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.constraint_schema = kcu.constraint_schema
        JOIN 
            information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.constraint_schema = tc.constraint_schema
        JOIN 
            information_schema.referential_constraints AS rc
            ON tc.constraint_name = rc.constraint_name
        WHERE 
            tc.constraint_type = 'FOREIGN KEY'
            AND kcu.constraint_schema = ANY(%s)
        ORDER BY 
            kcu.constraint_schema, kcu.table_name, kcu.constraint_name, kcu.ordinal_position;
        """

        # Dizionario per memorizzare i risultati
        foreign_keys = defaultdict(lambda: {
            "related_schema": None,
            "related_table": None,
            "related_columns": [],
            "onDelete": None,
            "onUpdate": None,
            "deferred": False
        })

        with self.conn.cursor() as cursor:
            cursor.execute(query, (self.schemas,))
            for row in cursor.fetchall():
                constraint_name, schema_name, table_name, column_name, related_schema, related_table, related_column, on_update, on_delete, is_deferrable, initially_deferred, ordinal_position = row
                key = (schema_name, table_name, constraint_name)
                foreign_keys[key]["related_schema"] = related_schema
                foreign_keys[key]["related_table"] = related_table
                foreign_keys[key]["related_columns"].append(related_column)
                foreign_keys[key]["onDelete"] = on_delete
                foreign_keys[key]["onUpdate"] = on_update
                foreign_keys[key]["deferred"] = is_deferrable == 'YES' and initially_deferred == 'YES'
                if "child_columns" not in foreign_keys[key]:
                    foreign_keys[key]["child_columns"] = []
                foreign_keys[key]["child_columns"].append(column_name)

        # Converti la chiave basata su singole colonne in una chiave con le colonne concatenate
        final_result = {}
        for key, value in foreign_keys.items():
            schema_name, table_name, constraint_name = key
            concatenated_columns = tuple(value["child_columns"])
            new_key = (schema_name, table_name, concatenated_columns)
            final_result[new_key] = {
                "related_schema": value["related_schema"],
                "related_table": value["related_table"],
                "related_columns": value["related_columns"],
                "onDelete": value["onDelete"],
                "onUpdate": value["onUpdate"],
                "deferred": value["deferred"]
            }

        return final_result
            
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
        

        try:
            self.connect()
            # Fetch all metadata and constraints/indices
            metadata = self.db.adapter.structure.get_info(schemas=self.schemas)
            self.process_metadata(db_structure, metadata)
            return db_structure
        except GnrNonExistingDbException:
            return {}
        finally:
            self.close_connection()

class SqlMigrator():
    def __init__(self,instance_name):
        self.application = GnrApp(instance_name)
        self.db = self.application.db
        self.ormStructure = OrmExtractor(self.db).get_json_struct()
        self.sqlStructure = DbExtractor(self.db).get_json_struct()

    def toSql(self,fromStructure=None):
        if fromStructure is None:
            fromStructure = self.sqlStructure
        self.commands = []
        self.diff = DeepDiff(fromStructure, self.ormStructure,
                              ignore_order=True,view='tree')
        for evt,dbchange in self.structChanges(self.diff):
            sql = getattr(self, f'{evt}_{dbchange["entity"]}' ,'missing_handler')(**dbchange)
            item = dbchange.get('item',{})
            schema_name = item.get('schema_name')
            table_name = item.get('table_name')
            column_name = item.get('column_name')
            self.commands.append({'sql':sql,'entity':dbchange['entity'],
                                  'entity_name':dbchange['entity_name'],
                                  'evt':evt,
                                  'schema_name':schema_name,
                                  'table_name':table_name,
                                  'column_name':column_name})
  
    def structChanges(self,diff):
        for key,evt in (('dictionary_item_added','added'),
                        ('dictionary_item_removed','removed'),
                        ('values_changed','changed')):
            for change in diff.get(key,[]):
                kw = dict(item=None)
                if evt == 'added':
                    kw['entity'] = change.t2['entity']
                    kw['entity_name'] = change.t2['entity_name']
                    kw['item'] = change.t2
                    kw['msg'] = 'Added {entity} {entity_name}: {item}'.format(**kw)

                elif evt == 'removed':
                    kw['entity'] = change.t1['entity']
                    kw['entity_name'] = change.t1['entity_name']
                    kw['item'] = change.t1
                    kw['msg'] = 'Removed {entity} {entity_name}: {item}'.format(**kw)

                if evt=='changed':
                    pathlist = change.path(output_format='list')
                    kw['changed_attribute'] = change.path(output_format='list')[-1]
                    changed_entity = change.up.up.t2
                    kw['entity'] = changed_entity['entity']
                    kw['entity_name'] = changed_entity['entity_name']
                    kw['newvalue'] = change.t2
                    kw['oldvalue'] = change.t1
                    kw['item'] = changed_entity
                    kw['msg'] = 'Changed {changed_attribute} in {entity} {entity_name} from {oldvalue} to {newvalue}'.format(**kw)
                yield evt,kw

        
    def added_db(self,item=None, **kwargs):
        result = []
        self.commands.append(self.db.adapter.createDbSql(item['entity_name'], 'UNICODE'))
        for schema in item['schemas'].values():
            result.append(self.added_schema(item=schema))
        return '\n'.join(result)

    def added_schema(self, item=None,**kwargs):
        result = []
        result.append(self.db.adapter.createSchemaSql(item['entity_name']))
        for table in item['tables'].values():
            result.append(self.added_table(item=table))
        return '\n'.join(result)


    def added_table(self, item=None,**kwargs):
        tablename = f'{self.db.adapter.adaptSqlName(item["schema_name"])}.{self.db.adapter.adaptSqlName(item["entity_name"])}'
        sqlfields = []
        for col in item['columns'].values():
            sqlfields.append(self.columnSql(col))
        sqlfields.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')
        return 'CREATE TABLE %s (%s);' % (tablename, ', '.join(sqlfields))

    def columnSql(self, col):
        """Return the statement string for creating a table's column"""
        colattr = col['attributes']
        return self.db.adapter.columnSqlDefinition(col['entity_name'],
                                                   dtype=colattr['dtype'], size=colattr.get('size'),
                                                   notnull=colattr.get('notnull', False),
                                                    unique=colattr.get('unique'),default=colattr.get('default'),
                                                    extra_sql=colattr.get('extra_sql'))

    def added_column(self, **kwargs):
        return f'added column {kwargs}'

    def removed_db(self, **kwargs):
        return f'removed db {kwargs}'

    def removed_schema(self, **kwargs):
        return f'removed schema {kwargs}'
    
    def removed_table(self, **kwargs):
        return f'removed table {kwargs}'

    def removed_column(self, **kwargs):
        return f'removed column {kwargs}'

    def changed_db(self, **kwargs):
        return f'changed db {kwargs}'

    def changed_schema(self, **kwargs):
        return f'changed schema {kwargs}'
    
    def changed_table(self, **kwargs):
        return f'changed table {kwargs}'

    def changed_column(self, **kwargs):
        return f'changed column {kwargs}'

    def missing_handler(self,**kwargs):
        return f'missing {kwargs}'

    def applyChanges(self):
        """TODO"""
        firstcommand = self.commands.pop(0)
        if firstcommand['entity_name'] == 'db':
            self.db.adapter.execute(firstcommand['sql'],manager=True)
        else:
            self.commands = [firstcommand]+self.commands
        sql = '\n'.join([c['sql'] for c in self.commands])
        self.db.adapter.execute(sql,autoCommit=True)

if __name__ == '__main__':

    #jsonorm = OrmExtractor(GnrApp('dbsetup_tester').db).get_json_struct()
    #with open('testorm.json','w') as f:
    #    f.write(json.dump(jsonorm))

    mig = SqlMigrator('dbsetup_tester')
    mig_1 = SqlMigrator('dbsetup_tester_1')
   #diff = compare_json({},mig.ormStructure)
   #print('\n---from 0 to 1 \n',diff)
    #diff = compare_json(mig_1.ormStructure,mig.ormStructure)
    #print('\n---from 1 to 0',diff)
    #print('orm mig1',mig_1.ormStructure)
    mig.toSql()
    mig.applyChanges()
    #print('\n'.join([c["sql"] for c in mig.commands]))
