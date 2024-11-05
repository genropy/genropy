import re

import json
import time
import functools
from collections import defaultdict

import attr
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
        schema_name = pkgobj.sqlname
        self.schemas[schema_name] = {
            'metadata':{},
            'schema_name':schema_name,
            'entity':'schema',
            'entity_name':schema_name,
            'tables':{}
        }
        for tblobj in pkgobj.tables.values():
            self.fill_json_table(tblobj)

    def fill_json_table(self,tblobj):
        schema_name = tblobj.pkg.sqlname
        table_name = tblobj.sqlname
        pkeys = ','.join([tblobj.column(col).sqlname for col in tblobj.attributes['pkey'].split(',')])
        self.schemas[schema_name]['tables'][table_name] = {
            "metadata": {},
            'entity':'table',
            'schema_name':schema_name,
            'table_name':table_name,
            'entity_name':table_name,
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
        attributes = self.convert_colattr(colobj)
        table_json = self.schemas[schema_name]['tables'][table_name]
        column_name = colobj.sqlname
        if column_name in table_json['attributes']['pkeys']:
            attributes['notnull'] = True
        table_json['columns'][colobj.sqlname] = {"entity":"column",
                                                "schema_name":schema_name,
                                                "table_name":table_name,
                                                "entity_name":column_name,
                                                "attributes":attributes}

    def convert_colattr(self,colobj):
        result =  {k:v for k,v in colobj.attributes.items() if k in self.col_json_keys and v is not None}
        size = result.pop('size',None)
        dtype = result.pop('dtype',None)
        if size:
            if size.startswith(':'):
                size = f'0{size}'
            if ':' in size:
                dtype = 'A'
            else:
                dtype = 'C'
        if dtype in ('A','C') and not size:
            dtype = 'T'
        result['dtype'] = dtype
        if size:
            result['size'] = size
        return result
    

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
        self.application_schemas = [pkg.sqlname for pkg in self.db.packages.values()]


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


            
    def process_metadata(self, metadata):
        """Processes schema, table, and column metadata."""
        for c in metadata:
            schema_name = c.pop('_pg_schema_name')
            table_name = c.pop('_pg_table_name')
            column_name = c.pop('name')
            colattr = {k:v for k,v in c.items()  if k in self.col_json_keys and v is not None}
            if colattr['notnull'] is False:
                colattr.pop('notnull')

            if schema_name not in self.json_schemas:
                self.json_schemas[schema_name] = {
                    "metadata": {},
                    "tables": {},
                    "entity":"schema",
                    "entity_name":schema_name,
                    "schema_name":schema_name
                }
            if table_name not in self.json_schemas[schema_name]["tables"]:
                self.json_schemas[schema_name]["tables"][table_name] = {
                    "metadata": {},
                    "columns": {},
                    "constraints": {},
                    "indices": {},
                    "entity":"table",
                    "attributes":{"pkeys":None},
                    "entity_name":table_name,
                    "table_name":table_name,
                    "schema_name":schema_name
                }
            if c.get('_pg_is_primary_key'):
                self.pkeys_dict[(schema_name,table_name)].append(column_name)
            self.json_schemas[schema_name]["tables"][table_name]["columns"][column_name] = {"entity":"column",
                                                                                      "schema_name":schema_name,
                                                                                      "table_name":table_name,
                                                                                      "entity_name":column_name,
                                                                                        "attributes":colattr}
    
    def process_primary_keys(self):
        for t,pkeys in self.pkeys_dict.items():
            schema_name,table_name = t
            self.json_schemas[schema_name]['tables'][table_name]['attributes']['pkeys'] = ','.join(pkeys)

    def process_foreign_keys(self,foreign_keys_dict=None):
        for t,fkeyattr in foreign_keys_dict.items():
            pass

    @measure_time
    def get_json_struct(self,metadata_only=False):
        """Generates the JSON structure of the database."""
        self.json_structure = {'root':{
            'schemas':{},
            'entity':'db',
            'entity_name':self.db.dbname
            }
        }
        self.json_schemas = self.json_structure["root"]['schemas']        
        self.pkeys_dict = defaultdict(list)
        try:
            self.connect()
            # Fetch all metadata and constraints/indices
            metadata = self.db.adapter.struct_get_schema_info(schemas=self.application_schemas)
            #foreign_keys_dict = self.db.adapter.struct_get_foreign_keys()
            self.process_metadata(metadata)
            self.process_primary_keys()
            #self.process_foreign_keys(foreign_keys_dict)
            return self.json_structure
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
        self.commands = defaultdict(list)
        self.diff = DeepDiff(fromStructure, self.ormStructure,
                              ignore_order=True,view='tree')
        for evt,dbchange in self.structChanges(self.diff):
            sql = getattr(self, f'{evt}_{dbchange["entity"]}' ,'missing_handler')(**dbchange)
            item = dbchange.get('item',{})
            schema_name = item.get('schema_name')
            table_name = item.get('table_name')
            column_name = item.get('column_name')
            entity_name = dbchange['entity_name']
            entity = dbchange['entity']
            command_key = ['db']
            if entity in ('table','column'):
                command_key.append(schema_name)
            if entity =='column' or (entity=='table' and evt=='upd'):
                command_key.append(table_name)
            command = {'sql':sql,'entity':dbchange['entity'],
                                    'entity_name':entity_name,
                                    'evt':evt,
                                    'schema_name':schema_name,
                                    'table_name':table_name,
                                    'column_name':column_name}
            self.commands[tuple(command_key)].append(command)


            

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
                    kw['action'] = 'REMOVE'
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
        tablename = self.tableSqlName(item)
        sqlfields = []
        for col in item['columns'].values():
            sqlfields.append(self.columnSql(col))
        sqlfields.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')
        return 'CREATE TABLE %s (%s);' % (tablename, ', '.join(sqlfields))


    def added_column(self, item=None,**kwargs):
        return f'ADD COLUMN {self.columnSql(item)}'

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

    def changed_column(self,item=None,changed_attribute=None, oldvalue=None,newvalue=None,**kwargs):
        if changed_attribute in ('size','dtype'):
            return f'changed_column {changed_attribute}' #self.alterColumnType(item,changed_attribute=changed_attribute,oldvalue=oldvalue,newvalue=newvalue)
        return
    
    #def xxx(self,col):
    #    new_dtype = col.attributes['dtype']
    #    if col.attributes.get('unaccent'):
    #        self.unaccent = True
    #    new_size = col.attributes.get('size')
    #    new_unique = col.attributes.get('unique')
    #    new_notnull = col.attributes.get('notnull')
    #    old_dtype = dbcolumns[col.sqlname]['dtype']
    #    old_size = dbcolumns[col.sqlname].get('size')
    #    old_notnull = dbcolumns[col.sqlname].get('notnull')
    #    if not 'pkey' in tblattr:
    #        raise GnrSqlException(f'Missing pkey in table {tbl.fullname}')
    #    if tblattr['pkey']==col.sqlname:
    #        new_notnull = old_notnull
    #    old_unique = self.unique_constraints['%s.%s.%s'%(tbl.sqlschema,tbl.sqlname,col.sqlname)]
    #    if not self.unique_constraints and col.sqlname in columnsindexes:
    #        if tblattr['pkey']==col.sqlname:
    #            old_unique = new_unique
    #        else:
    #            old_unique = columnsindexes[col.sqlname].get('unique')
    #    if new_dtype == 'A' and not new_size:
    #        new_dtype = 'T'
    #    if new_dtype == 'A' and not ':' in new_size:
    #        new_dtype = 'C'
    #    if new_size and ':' in new_size:
    #        t1, t2 = new_size.split(':')
    #        new_size = '%s:%s' % (t1 or '0', t2)
    #    if new_size and new_dtype == 'N' and not ',' in new_size:
    #        new_size = '%s,0' % new_size
    #    if new_dtype in ('X', 'Z', 'P') and old_dtype == 'T':
    #        pass
    #    elif new_dtype=='serial' and old_dtype=='L':
    #        pass
    #    elif new_dtype in ('L','I') and old_dtype in ('L','I') and not self.db.adapter.allowAlterColumn:
    #        pass
    #    elif new_dtype != old_dtype or new_size != old_size or bool(old_unique)!=bool(new_unique) or bool(old_notnull)!=bool(new_notnull):
    #        if (new_dtype != old_dtype or new_size != old_size):
    #            change = self._alterColumnType(col, new_dtype, new_size=new_size)
    #            self.changes.append(change)
    #        if bool(old_unique)!=bool(new_unique):
    #            self.changes.append(self._alterUnique(col,new_unique,old_unique))
    #        if bool(old_notnull)!=bool(new_notnull):
    #            self.changes.append(self._alterNotNull(col,new_notnull, old_notnull))
#
#
    #    return f'changed column {kwargs}'

    def missing_handler(self,**kwargs):
        return f'missing {kwargs}'


    def columnSql(self, col):
        """Return the statement string for creating a table's column"""
        colattr = col['attributes']
        return self.db.adapter.columnSqlDefinition(col['entity_name'],
                                                   dtype=colattr['dtype'], size=colattr.get('size'),
                                                   notnull=colattr.get('notnull', False),
                                                    unique=colattr.get('unique'),default=colattr.get('default'),
                                                    extra_sql=colattr.get('extra_sql'))
    
    
    #def alterColumnType(self, item=None,changed_attribute=None,oldvalue=None,newvalue=None):
    #    """Prepare the sql statement for altering the type of a given column and return it"""
    #    attributes = item['attributes']
    #    size = attributes.get('size')
    #    if size and size.startswith(':'):
    #        size = f'0{size}'
    #    sqlType = self.db.adapter.columnSqlType(attributes['dtype'], size)
    #    rebuildColumn = None
    #    if changed_attribute=='size' or (oldvalue in ('T','A','C')) and (newvalue in ('T','A','C')):
    #        rebuildColumn = False
    #        sqlType = self.db.adapter.columnSqlType(attributes['dtype'], attributes['size'])
    #        return self.db.adapter.alterColumnSql(column=item['entity_name'], dtype=sqlType)
    #    else:
    #        usedColumn = self.db.adapter.raw_fetch(f'SELECT COUNT(*) FROM {self.tableSqlName(item)};')
    #        if usedColumn:
    #            rebuildColumn = False
    #        else:
    #            rebuildColumn = True
    #    if rebuildColumn:
    #        return ',\n'.join([f'DROP COLUMN {item['entity_name']}'  ,f"ADD COLUMN {self.columnSql(item)}"])
    #    else:
    #        sqlType = self.db.adapter.columnSqlType(attributes['dtype'], attributes['size'])
    #        return self.db.adapter.alterColumnSql(column=item['entity_name'], dtype=sqlType)
        
    def tableSqlName(self,item=None):
        schema_name = item['schema_name']
        table_name = item['table_name'] 
        return f'{self.db.adapter.adaptSqlName(schema_name)}.{self.db.adapter.adaptSqlName(table_name)}'
                              
    def applyChanges(self):
        """TODO"""
        firstcommand = self.commands.pop(0)
        if firstcommand['entity_name'] == 'db':
            self.db.adapter.execute(firstcommand['sql'],manager=True)
        else:
            self.commands = [firstcommand]+self.commands
        sql = '\n'.join([c['sql'] for c in self.commands if c['sql']])
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
    #mig.applyChanges()
    #print('\n'.join([c["sql"] for c in mig.commands]))
