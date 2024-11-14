import re
import hashlib

import json
import time
import functools
from collections import defaultdict

from deepdiff import DeepDiff
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrdict import dictExtract
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException
from pyparsing import col

COL_JSON_KEYS = ("dtype","notnull","default","size","unique")

def nested_defaultdict():
    return defaultdict(nested_defaultdict)



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



 
def hashed_name(schema, table, columns, obj_type='idx'):
    """
    Generate a unique name for constraints or indexes using a hash.

    Parameters:
    - schema (str): The name of the schema.
    - table (str): The name of the table.
    - columns (list): List of columns involved in the constraint or index.
    - obj_type (str): Type of object ('idx' for index, 'fk' for foreign key constraint, etc.).

    Returns:
    - str: A unique name for the constraint or index.
    """
    # Concatena i dettagli in una stringa univoca
    columns_str = "_".join(columns)  # Unisci i nomi delle colonne
    identifier = f"{schema}_{table}_{columns_str}_{obj_type}"
    # Calcola l'hash e tronca a 8 caratteri
    hash_suffix = hashlib.md5(identifier.encode()).hexdigest()[:8]
    # Costruisci il nome finale con prefisso e hash
    return f"{obj_type}_{hash_suffix}"



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
        pkeys = ','.join([tblobj.column(col).sqlname for col in tblobj.pkeys]) if tblobj.pkeys else None
        constraints = {}
        indexes = {}
        self.schemas[schema_name]['tables'][table_name] = {
            "metadata": {},
            'entity':'table',
            'schema_name':schema_name,
            'table_name':table_name,
            'entity_name':table_name,
            "attributes":{"pkeys":pkeys},
            "columns": {},
            "constraints": constraints,
            "indexes": indexes
        }
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj,constraints=constraints,indexes=indexes)
        for compositecol in tblobj.composite_columns.values():
            pass

    def fill_json_column(self,colobj,constraints=None,indexes=None):
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        colattr = colobj.attributes
        attributes = self.convert_colattr(colattr)
        table_json = self.schemas[schema_name]['tables'][table_name]
        column_name = colobj.sqlname
        table_json['columns'][colobj.sqlname] = {"entity":"column",
                                                "schema_name":schema_name,
                                                "table_name":table_name,
                                                "entity_name":column_name,
                                                "attributes":attributes}
        joiner =  colobj.relatedColumnJoiner()
        indexed = colattr.get('indexed')
        if joiner and joiner.get('mode')=='foreignkey':
            pass
            #constraint = {k[0:-4]:v for k,v in joiner.keys() if k.endswith('_sql')}
            #constraint['related_field'] = joiner['one_relation'] #'alfa.ricetta.codice
            #constraints[joiner['many_reltion']] = constraint
            #print('joiner',joiner)
        if indexed:
            indexed_json = self.handle_indexed(colobj=colobj,indexed=indexed)
            index_name = hashed_name(schema=schema_name,table=table_name,columns=list(indexed_json.keys()))
            indexes[index_name] = {
                "entity":"index",
                "entity_name":index_name,
                "schema_name":schema_name,
                "table_name":table_name,
                "attributes":indexed_json
            }

    def handle_indexed(self,colobj,indexed=None):
        indexed = {} if indexed in (True,'Y') else dict(indexed)
        withpars = dictExtract(indexed,'with_',pop=True)
        sorting = indexed.pop('sorting',None)
        columns = (colobj.attributes.get('composed_of') or colobj.name).split(',')
        sorting = sorting.split(',') if sorting else [None] * len(columns)
        return dict(
            columns=dict(zip(columns,sorting)),
            indexwith=withpars,
            **indexed
        )

    def convert_colattr(self,colattr):
        result =  {k:v for k,v in colattr.items() if k in self.col_json_keys and v is not None}
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

    def fetch_constraints_and_indexes(self):
        """Fetches all constraints and indexes for tables."""
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

    def process_constraints_and_indexes(self, db_structure, constraints_and_indexes):
        """Processes constraints and indexes data."""
        for (schema_name, table_name, constraint_name, constraint_type, column_name, 
            referenced_table_schema, referenced_table_name, referenced_column_name, index_name, index_def) in constraints_and_indexes:
            
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
            # Ensure the indexes dictionary exists
            if "indexes" not in db_structure[schema_name]["tables"][table_name]:
                db_structure[schema_name]["tables"][table_name]["indexes"] = {}

            # Parse the index definition and store relevant details
            if index_name:
                index_info = self.parse_index_definition(index_def)
                db_structure[schema_name]["tables"][table_name]["indexes"][index_name] = {
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
            is_nullable = c.pop('_pg_is_nullable')
            column_name = c.pop('name')
            colattr = {k:v for k,v in c.items()  if k in self.col_json_keys and v is not None}
            if colattr.get('notnull') is False:
                colattr.pop('notnull')

            if schema_name not in self.json_schemas:
                self.json_schemas[schema_name] = {
                    "metadata": {},
                    "tables": {},
                    "entity":"schema",
                    "entity_name":schema_name,
                    "schema_name":schema_name
                }
            if table_name and table_name not in self.json_schemas[schema_name]["tables"]:
                self.json_schemas[schema_name]["tables"][table_name] = {
                    "metadata": {},
                    "columns": {},
                    "constraints": {},
                    "indexes": {},
                    "entity":"table",
                    "attributes":{"pkeys":None},
                    "entity_name":table_name,
                    "table_name":table_name,
                    "schema_name":schema_name
                }
            if column_name:
                if c.get('_pg_is_primary_key'):
                    self.pkeys_dict[(schema_name,table_name)].append(column_name)
                elif is_nullable=='NO':
                    colattr['notnull'] = True
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
            # Fetch all metadata and constraints/indexes
            if self.application_schemas:
                metadata = self.db.adapter.struct_get_schema_info(schemas=self.application_schemas)
                foreign_keys_dict = self.db.adapter.struct_get_foreign_keys(schemas=self.application_schemas)
                self.process_metadata(metadata)
                self.process_primary_keys()
                #self.process_foreign_keys(foreign_keys_dict)
            return self.json_structure
        except GnrNonExistingDbException:
            return {}
        finally:
            self.close_connection()

class SqlMigrator():
    def __init__(self,db):
        self.db = db
        self.commands = nested_defaultdict()
        self.sql_commands = {'db_creation':None,'build_commands':None}

    def extractSql(self):
        self.sqlStructure = DbExtractor(self.db).get_json_struct()
    
    def extractOrm(self):
        self.ormStructure = OrmExtractor(self.db).get_json_struct()
    
    def clearSql(self):
        self.sqlStructure = {}

    def clearOrm(self):
        self.ormStructure = {}

    def setDiff(self):
        self.diff = DeepDiff(self.sqlStructure, self.ormStructure,
                              ignore_order=True,view='tree')

    def clearCommands(self):
        self.commands.pop('db',None) #rebuils
        
    def toSql(self):
        self.extractSql()
        self.extractOrm()
        self.setDiff()
        self.clearCommands()
        for evt,kw in self.structChanges(self.diff):
            handler = getattr(self, f'{evt}_{kw["entity"]}' ,'missing_handler')
            handler(**kw)
 
    def structChanges(self,diff):
        for key,evt in (('dictionary_item_added','added'),
                        ('dictionary_item_removed','removed'),
                        ('values_changed','changed'),('type_changes','changed')):
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

        
    def schema_tables(self,schema_name):
        return self.commands['db']['schemas'][schema_name]['tables']

    def added_db(self,item=None, **kwargs):
        self.commands['db']['command'] = self.db.adapter.createDbSql(item['entity_name'], 'UNICODE')
        for schema in item['schemas'].values():
            self.added_schema(item=schema)

    def added_schema(self, item=None,**kwargs):
        schema_name = item['entity_name']
        self.commands['db']['schemas'][schema_name]['command'] = self.db.adapter.createSchemaSql(schema_name)
        for table in item['tables'].values():
            self.added_table(item=table)

    def added_table(self, item=None,**kwargs):
        sqltablename = self.tableSqlName(item)
        sqlfields = []
        sqlconstraints = []
        for col in item['columns'].values():
            sqlfields.append(self.columnSql(col))
        for constr in item['constraints'].values():
            sqlconstraints.append(self.constraintSql(constr))
        if item["attributes"]["pkeys"]:
            sqlfields.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')
        sql = f"CREATE TABLE {sqltablename} ({', '.join(sqlfields)});"
        self.schema_tables(item['schema_name'])[item['table_name']]['command'] = sql
        for item in item['indexes'].values():
            self.added_index(item=item)

    def added_column(self, item=None,**kwargs):
        sql =  f'ADD COLUMN {self.columnSql(item)}'
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns'] 
        columns_dict[item['entity_name']]['command'] = sql

    def added_index(self, item=None,**kwargs):
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes'] 
        indexes_dict[item['entity_name']]['command'] = self.createIndexSql(item)

    def changed_table(self, item=None, changed_attribute=None, oldvalue=None, newvalue=None, **kwargs):
        """
        Handles changes in table attributes, such as primary keys and unique constraints.
        """
        schema_name = item['schema_name']
        table_name = item['table_name']
        if changed_attribute == 'pkeys':
            drop_pk_sql = self.db.adapter.struct_drop_table_pkey_sql(schema_name,table_name)
            add_pk_sql =  self.db.adapter.struct_add_table_pkey_sql(schema_name,table_name,newvalue)
            self.schema_tables(schema_name)[table_name]['command'] = f"{drop_pk_sql}\n{add_pk_sql}"

    def changed_column(self,item=None,changed_attribute=None, oldvalue=None,newvalue=None,**kwargs):
        if changed_attribute in ('size','dtype'):
            return f'changed_column {changed_attribute}' #self.alterColumnType(item,changed_attribute=changed_attribute,oldvalue=oldvalue,newvalue=newvalue)
        return
    
    def changed_index(self, item=None,**kwargs):
        pass

    def removed_db(self, **kwargs):
        return f'removed db {kwargs}'

    def removed_schema(self, **kwargs):
        return f'removed schema {kwargs}'
    
    def removed_table(self, **kwargs):
        return f'removed table {kwargs}'

    def removed_column(self, **kwargs):
        return f'removed column {kwargs}'

    def removed_index(self, item=None,**kwargs):
        pass


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
    
    def constraintSql(self,const_item):
        pass
    
    def createIndexSql(self,index_item):
        # Extract main information from the dictionary
        index_name = index_item.get("entity_name", "")
        attributes = index_item.get("attributes", {})
        columns = attributes.get("columns", {})
        method = attributes.get("method", "btree")
        with_options = attributes.get("with", {})
        tablespace = attributes.get("tablespace", "")
        where_clause = attributes.get("where", "")
        
        # Build the list of columns with specific sorting if present
        column_defs = []
        for column, order in columns.items():
            if order:
                column_defs.append(f"{column} {order}")
            else:
                column_defs.append(f"{column}")  # Default sorting if not specified

        # Join columns into a single string
        column_list = ", ".join(column_defs)

        # Build the WITH options clause
        with_parts = [f"{key} = {value}" for key, value in with_options.items()]
        with_clause = f"WITH ({', '.join(with_parts)})" if with_parts else ""
        
        # Add TABLESPACE clause if specified
        tablespace_clause = f"TABLESPACE {tablespace}" if tablespace else ""
        
        # Add WHERE clause if specified
        where_clause = f"WHERE {where_clause}" if where_clause else ""
        
        # Build full table name with schema if schema is provided
        full_table_name = self.tableSqlName(item=index_item)
        
        # Compose the final SQL statement
        sql = f"""
        CREATE INDEX {index_name}
        ON {full_table_name}
        USING {method} ({column_list})
        {with_clause}
        {tablespace_clause}
        {where_clause};
        """
        
        # Return a clean, single-line SQL string
        return " ".join(sql.split())
    
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

    def getChanges(self):
        commands = self.commands
        dbitem = commands['db']
        sql_command = dbitem.get('command')
        schemas = dbitem.get('schemas',{})
        if sql_command:
            self.sql_commands['db_creation'] = sql_command
        commandlist = []
        #constrainList = []
        for schema_name,schema_item in schemas.items():
            sql_command =schema_item.get('command')
            tables = schema_item.get('tables',{})
            if sql_command:
                commandlist.append(sql_command)
            for table_name,tbl_item in tables.items():
                col_commands = ',\n'.join([colitem['command'] for colitem in tbl_item['columns'].values()])
                index_commands = ',\n'.join([colitem['command'] for colitem in tbl_item['indexes'].values()])

                #constraints_commands = ',\n'.join([colitem['command'] for colitem in tbl_item['constraints'].values()])
                #constrainList.append(constraints_commands)
                tbl_command = tbl_item.get('command')
                if col_commands and not tbl_command:
                    tbl_item['command'] = f"""ALTER TABLE "{schema_name}"."{table_name}" """
                commandlist.append(f"{tbl_item['command']}\n {col_commands};" if  col_commands else tbl_item['command'])
                if index_commands:
                    commandlist.append(index_commands)
        self.sql_commands['build_commands'] = '\n'.join(commandlist)
        return '\n'.join(self.sql_commands.values())

    def applyChanges(self):
        self.getChanges()
        db_creation = self.sql_commands.pop('db_creation',None)
        if db_creation:
            self.db.adapter.execute(db_creation,manager=True)
        build_commands = self.sql_commands.pop('build_commands',None)
        if build_commands:
            self.db.adapter.execute(build_commands,autoCommit=True)

if __name__ == '__main__':

    #jsonorm = OrmExtractor(GnrApp('dbsetup_tester').db).get_json_struct()
    #with open('testorm.json','w') as f:
    #    f.write(json.dump(jsonorm))
    app = GnrApp('dbsetup_tester')
    mig = SqlMigrator(app.db)
   #diff = compare_json({},mig.ormStructure)
   #print('\n---from 0 to 1 \n',diff)
    #diff = compare_json(mig_1.ormStructure,mig.ormStructure)
    #print('\n---from 1 to 0',diff)
    #print('orm mig1',mig_1.ormStructure)
    mig.extractSql()
    #mig.applyChanges()
    #print('\n'.join([c["sql"] for c in mig.commands]))