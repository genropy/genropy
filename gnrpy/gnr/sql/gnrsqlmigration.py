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


COL_JSON_KEYS = ("dtype","notnull","default","size","unique")

def nested_defaultdict():
    return defaultdict(nested_defaultdict)


def camel_to_snake(camel_str):
    """
    Convert a camelCase string to snake_case.
    
    Args:
        camel_str (str): The string in camelCase format.
    
    Returns:
        str: The string converted to snake_case.
    """
    # Replace uppercase letters with _ followed by lowercase, except at the start
    snake_str = re.sub(r'(?<!^)([A-Z])', r'_\1', camel_str)
    return snake_str.lower()



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



def clean_attributes(attributes):
    return {k:v for k,v in attributes.items() if v not in (None,{},False,[],'', "NO ACTION")}
    

 
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
        self.deferred_indexes = []

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
            "relations":{},
            "constraints": constraints,
            "indexes": indexes
        }
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj)
        for compositecol in tblobj.composite_columns.values():
            self.handle_relations_and_indexes(compositecol)


    def fill_json_column(self,colobj):
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        colattr = colobj.attributes
        attributes = self.convert_colattr(colattr)
        table_json = self.schemas[schema_name]['tables'][table_name]
        column_name = colobj.sqlname
        pkeys = table_json['attributes']['pkeys']
        if pkeys and (column_name in pkeys.split(',')):
            attributes['notnull'] = '_auto_'
        table_json['columns'][colobj.sqlname] = {"entity":"column",
                                                "schema_name":schema_name,
                                                "table_name":table_name,
                                                "entity_name":column_name,
                                                "attributes":attributes}
        self.handle_relations_and_indexes(colobj)
    
    def handle_relations_and_indexes(self,colobj):
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        colattr = colobj.attributes
        joiner =  colobj.relatedColumnJoiner()
        indexed = colattr.get('indexed')
        table_json = self.schemas[schema_name]['tables'][table_name]
        if joiner and joiner.get('foreignkey'):
            relation_json = self.handle_column_relation(colobj=colobj,joiner=joiner)
            table_json["relations"][relation_json["entity_name"]] = relation_json
        if indexed:
            indexed_json = self.handle_column_indexed(colobj=colobj,indexed=indexed)
            table_json["indexes"][indexed_json["entity_name"]] = indexed_json


    def statement_converter(self, command):
        if not command: return None
        command = command.upper()
        if command in ('R', 'RESTRICT'):
            return 'RESTRICT'
        elif command in ('C', 'CASCADE'):
            return 'CASCADE'
        elif command in ('N', 'NO ACTION'):
            return 'NO ACTION'
        elif command in ('SN', 'SETNULL', 'SET NULL'):
            return 'SET NULL'
        elif command in ('SD', 'SETDEFAULT', 'SET DEFAULT'):
            return 'SET DEFAULT'
            

    def handle_column_relation(self,colobj,joiner=None):
        columns = (colobj.attributes.get('composed_of') or colobj.name).split(',')
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=columns,obj_type='fk')
        attributes = {camel_to_snake(k[0:-4]):self.statement_converter(v) for k,v in joiner.items() if k.endswith('_sql')}
        attributes['constraint_name'] = hashed_entity_name
        attributes['columns'] = columns
        related_field = joiner['one_relation'] #'alfa.ricetta.codice
        related_table,related_column = related_field.rsplit('.',1)
        rel_tblobj = colobj.db.table(related_table)
        rel_colobj = rel_tblobj.column(related_column)
        

        attributes['related_columns'] = (rel_colobj.attributes.get('composed_of') or rel_colobj.name).split(',')
        attributes['related_table'] = rel_colobj.table.sqlname
        attributes['related_schema'] = rel_colobj.table.pkg.sqlname
        attributes['constraint_name'] = hashed_entity_name
        attributes['constraint_type'] = "FOREIGN KEY"
        result = {"entity": "relation",
                    "entity_name": hashed_entity_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "attributes":attributes}
        if attributes['related_columns'] != rel_tblobj.pkeys:
            self.deferred_indexes.append(colobj)

        return result
    
    def handle_column_indexed(self,colobj,indexed=None):
        indexed = {} if indexed in (True,'Y') else dict(indexed)
        with_options = dictExtract(indexed,'with_',pop=True)
        sorting = indexed.pop('sorting',None)
        columns = (colobj.attributes.get('composed_of') or colobj.name).split(',')
        sorting = sorting.split(',') if sorting else [None] * len(columns)
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=columns)
        attributes = dict(
            columns=dict(zip(columns,sorting)),
            with_options=with_options,
            index_name=hashed_entity_name,
            **indexed
        )
        result = {"entity": "index",
                    "entity_name": hashed_entity_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "attributes":clean_attributes(attributes)}
        return result
        

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
        for colobj in self.deferred_indexes:
            table_name = colobj.table.sqlname
            schema_name = colobj.table.pkg.sqlname
            table_json = self.schemas[schema_name]['tables'][table_name]
            indexed_json = self.handle_column_indexed(colobj=colobj,indexed=True)
            table_json["indexes"][indexed_json["entity_name"]] = indexed_json
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
        infodict = self.get_info_from_db()
        if infodict is False:
            return {}
        for k,v in infodict.items():
            getattr(self,f'process_{k}')(v)
        return self.json_structure
            

    def get_info_from_db(self):
        result = {}
        try:
            self.connect()
            if self.application_schemas:
                adapter = self.db.adapter
                result["base_structure"] = adapter.struct_get_schema_info(schemas=self.application_schemas)
                result["constraints"] = adapter.struct_get_constraints(schemas=self.application_schemas)
                result["indexes"] = adapter.struct_get_indexes(schemas=self.application_schemas)
        except GnrNonExistingDbException:
            result = False
        finally:
            self.close_connection()
        return result

 
    def process_base_structure(self, base_structure):
        """Processes schema, table, and column metadata."""
        for c in base_structure:
            schema_name = c.pop('_pg_schema_name')
            table_name = c.pop('_pg_table_name')
            is_nullable = c.pop('_pg_is_nullable')
            column_name = c.pop('name')
            colattr = {k:v for k,v in c.items()  if k in self.col_json_keys and v is not None}
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
                    "relations":{},
                    "constraints": {},
                    "indexes": {},
                    "entity":"table",
                    "attributes":{"pkeys":None},
                    "entity_name":table_name,
                    "table_name":table_name,
                    "schema_name":schema_name
                }
            if column_name:
                if is_nullable=='NO':
                    colattr['notnull'] = True
                self.json_schemas[schema_name]["tables"][table_name]["columns"][column_name] = {"entity":"column",
                                                                                        "schema_name":schema_name,
                                                                                        "table_name":table_name,
                                                                                        "entity_name":column_name,
                                                                                            "attributes":colattr}

    def process_constraints(self,constraints_dict):
        for tablepath,constraints_by_type in constraints_dict.items():
            schema_name,table_name  = tablepath
            d = dict(constraints_by_type)
            table_json = self.json_schemas[schema_name]["tables"][table_name]
            primary_key_const = d.pop("PRIMARY KEY",{})
            if primary_key_const:
                pkeys = primary_key_const["columns"]
                table_json['attributes']['pkeys'] = ','.join(pkeys)
                for col in pkeys:
                    table_json['columns'][col]['attributes']['notnull'] = '_auto_'
            unique = d.pop("UNIQUE",{})
            multiple_unique = dict(unique)
            for k,v in unique.items():
                columns = v['columns']
                if len(columns)==1:
                    multiple_unique.pop(k)
                    self.json_schemas[schema_name]["tables"][table_name]['columns'][columns[0]]['attributes']['unique'] = True
            if multiple_unique:
                d['UNIQUE'] = multiple_unique
            self.process_table_relations(schema_name,table_name,d.pop('FOREIGN KEY',{}))
            d.pop('CHECK',None) # avoid for now
            for v in d.values():
                v['entity'] = 'constraint'
                v['entity_name'] = v['constraint_name']
            table_json['constraints'] = d

    def process_table_relations(self,schema_name,table_name,foreign_keys_dict):
        relations = self.json_schemas[schema_name]["tables"][table_name]['relations']
        for entity_name,entity_attributes in foreign_keys_dict.items():
            entity_attributes = clean_attributes(entity_attributes)
            hashed_entity_name = hashed_name(schema=schema_name,table=table_name,
                                             columns=entity_attributes['columns'],obj_type='fk')
            relations[hashed_entity_name] = {"entity":"relation",
                                             "entity_name":hashed_entity_name,
                                             "schema_name":schema_name,
                                             "table_name":table_name,
                                             "attributes":entity_attributes}
            

    def process_indexes(self,indexes_dict):
        for tablepath,index_dict in indexes_dict.items():
            schema_name,table_name  = tablepath
            d = dict(index_dict)
            table_json = self.json_schemas[schema_name]["tables"][table_name]
            for index_name,index_attributes in d.items():
                if index_attributes.get('constraint_type'):
                    continue
                hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=index_attributes['columns'])
                index_attributes = clean_attributes(index_attributes)
                index_attributes['index_name'] = index_name
                table_json['indexes'][hashed_entity_name] = {"table_name":table_name,
                                        "schema_name":schema_name,
                                        "entity_name":hashed_entity_name,
                                        "entity":"index","attributes":index_attributes}
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

        with open('testsqlextractor.json','w') as f:
            f.write(json.dumps(self.sqlStructure))

        with open('testormextractor.json','w') as f:
            f.write(json.dumps(self.ormStructure))

        for evt,kw in self.structChanges(self.diff):
            handler = getattr(self, f'{evt}_{kw["entity"]}' ,'missing_handler')
            handler(**kw)
 
    def structChanges(self,diff):
        for key,evt in (('dictionary_item_added','added'),
                        ('dictionary_item_removed','removed'),
                        ('values_changed','changed'),('type_changes','changed')):
            for change in diff.get(key,[]):
                if change.t2=='_auto_':
                    #auto-set for alignment to sql
                    continue
                kw = dict(item=None)
                pathlist = change.path(output_format='list')
                changed_attribute = self.get_changed_attribute(pathlist)
                if changed_attribute:
                    change = self.get_changed_entity(change)
                    evt = 'changed'
                    #if add or remove attribute it will be handled as a change of the entity
                if evt == 'added':
                    kw['entity'] = change.t2['entity']
                    kw['entity_name'] = change.t2['entity_name']
                    kw['item'] = change.t2
                elif evt == 'removed':
                    kw['action'] = 'REMOVE'
                    kw['entity'] = change.t1['entity']
                    kw['entity_name'] = change.t1['entity_name']
                    kw['item'] = change.t1
                if evt=='changed':
                    changed_entity = change.t2
                    kw['entity'] = changed_entity['entity']
                    kw['entity_name'] = changed_entity['entity_name']
                    kw['changed_attribute'] = changed_attribute
                    kw['newvalue'] = change.t2['attributes'].get(changed_attribute)
                    kw['oldvalue'] = change.t1['attributes'].get(changed_attribute)
                    kw['item'] = changed_entity
                yield evt,kw

    def get_changed_entity(self,change):
        changed_entity = change.t2
        while not isinstance(changed_entity,dict) or ('entity' not in changed_entity):
            change = change.up
            changed_entity = change.t2
        return change

    def get_changed_attribute(self,pathlist):
        """
        Find the element that comes immediately after 'attributes' in the list.

        Parameters:
            pathlist (list): The list of strings to search.

        Returns:
            str: The element after 'attributes', or None if not found.
        """
        if 'attributes' in pathlist:
            attr_index = pathlist.index('attributes')  # Find the index of 'attributes'
            if attr_index < len(pathlist) - 1:         # Ensure there is a next element
                return pathlist[attr_index + 1]
        return None

        
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
        substatements = []
        for col in item['columns'].values():
            substatements.append(self.columnSql(col))
        if item["attributes"]["pkeys"]:
            substatements.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')
        for rel_item in item['relations'].values():
            fkey_sql =  self.db.adapter.struct_foreign_key_sql(
                fk_name=rel_item['entity_name'],
                columns=rel_item['attributes']['columns'],
                related_table=rel_item['attributes']['related_table'],
                related_schema=rel_item['attributes']['related_schema'],
                related_columns=rel_item['attributes']['related_columns'],
                on_delete=rel_item['attributes'].get('on_delete'),
                on_update=rel_item['attributes'].get('on_update')
            )
            substatements.append(fkey_sql)
        for const_item in item['constraints'].values():  
            const_sql = self.db.adapter.struct_constraint_sql(
                schema_name=const_item['schema_name'],
                table_name=const_item['table_name'],
                constraint_name=const_item['entity_name'],
                constraint_type=const_item['attributes']['constraint_type'],
                columns=const_item['attributes']['columns']
            )
            substatements.append(const_sql)

        sql = f"CREATE TABLE {sqltablename} ({', '.join(substatements)});"
        self.schema_tables(item['schema_name'])[item['table_name']]['command'] = sql

                      

        for index_item in item['indexes'].values():
            self.added_index(item=index_item)

    def added_column(self, item=None,**kwargs):
        sql =  f'ADD COLUMN {self.columnSql(item)}'
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns'] 
        columns_dict[item['entity_name']]['command'] = sql

    def added_index(self, item=None,**kwargs):
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes'] 
        indexes_dict[item['entity_name']]['command'] = self.createIndexSql(item)

    def added_relation(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle the addition of a new relation (foreign key).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        sql =  self.db.adapter.struct_foreign_key_sql(
                fk_name=item['entity_name'],
                columns=item['attributes']['columns'],
                related_table=item['attributes']['related_table'],
                related_schema=item['attributes']['related_schema'],
                related_columns=item['attributes']['related_columns'],
                on_delete=item['attributes'].get('on_delete'),
                on_update=item['attributes'].get('on_update')
            )
        relations_dict[item['entity_name']] = {
            "command":f'ADD {sql};'
        }

    def added_constraint(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle the addition of a new constraint (e.g., UNIQUE).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        sql = self.db.adapter.struct_constraint_sql(
                schema_name=item['schema_name'],
                table_name=item['table_name'],
                constraint_name=item['entity_name'],
                constraint_type=item['attributes']['constraint_type'],
                columns=item['attributes']['columns']
            )
        constraints_dict[item['entity_name']] = {
            "command": f'ADD {sql};'
        }

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



    def changed_column(self, item=None, changed_attribute=None, oldvalue=None, newvalue=None, **kwargs):
        """
        *autogenerated*
        Handle changes to a column's attributes (e.g., size, dtype, notnull, unique).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns']
        column_name = item['entity_name']

        if changed_attribute == 'dtype' or changed_attribute == 'size':
            # Handle changes to data type or size
            new_sql_type = self.db.adapter.columnSqlType(dtype=newvalue, size=item['attributes'].get('size'))
            columns_dict[column_name]['command'] = self.db.adapter.struct_alter_column(
                schema_name=item['schema_name'],
                table_name=item['table_name'],
                column_name=column_name,
                new_sql_type=new_sql_type
            )
        elif changed_attribute == 'notnull':
            # Handle changes to the NOT NULL constraint
            if newvalue:
                columns_dict[column_name]['command'] = self.db.adapter.struct_add_not_null(
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                    column_name=column_name
                )
            else:
                columns_dict[column_name]['command'] = self.db.adapter.struct_drop_not_null(
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                    column_name=column_name
                )
        elif changed_attribute == 'unique':
            # Handle changes to the UNIQUE constraint
            if newvalue:
                columns_dict[column_name]['command'] = self.db.adapter.struct_add_unique_constraint(
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                    column_name=column_name
                )
            else:
                columns_dict[column_name]['command'] = self.db.adapter.struct_drop_unique_constraint(
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                    column_name=column_name
                )

    def changed_index(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle changes to an index.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes']
        index_name = item['entity_name']
        old_command = indexes_dict[index_name]['command']
        new_command = self.createIndexSql(item)
        indexes_dict[index_name]['command'] = f"DROP INDEX IF EXISTS {index_name};\n{new_command}"

    def changed_relation(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle changes to a relation (foreign key).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        relation_name = item['entity_name']
        old_command = relations_dict[relation_name]['command']
        new_command = self.db.adapter.struct_foreign_key_sql(
            schema_name=item['schema_name'],
            table_name=item['table_name'],
            fk_name=item['entity_name'],
            columns=item['attributes']['columns'],
            related_table=item['attributes']['related_table'],
            related_schema=item['attributes']['related_schema'],
            related_columns=item['attributes']['related_columns'],
            on_delete=item['attributes'].get('on_delete'),
            on_update=item['attributes'].get('on_update')
        )
        relations_dict[relation_name]['command'] = f"ALTER TABLE {item['schema_name']}.{item['table_name']} DROP CONSTRAINT {relation_name};\n{new_command}"

    def changed_constraint(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle changes to a constraint.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        constraint_name = item['entity_name']
        old_command = constraints_dict[constraint_name]['command']
        new_command = self.db.adapter.struct_add_constraint_sql(
            schema_name=item['schema_name'],
            table_name=item['table_name'],
            constraint_name=item['entity_name'],
            constraint_type=item['attributes']['constraint_type'],
            columns=item['attributes']['columns']
        )
        constraints_dict[constraint_name]['command'] = f"ALTER TABLE {item['schema_name']}.{item['table_name']} DROP CONSTRAINT {constraint_name};\n{new_command}"

    def removed_index(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle the removal of an index.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes']
        index_name = item['entity_name']
        indexes_dict[index_name] = {
            "command": f"DROP INDEX IF EXISTS {index_name};"
        }

    def removed_relation(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle the removal of a relation (foreign key).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        relation_name = item['entity_name']
        relations_dict[relation_name] = {
            "command": f"ALTER TABLE {item['schema_name']}.{item['table_name']} DROP CONSTRAINT {relation_name};"
        }

    def removed_constraint(self, item=None, **kwargs):
        """
        *autogenerated*
        Handle the removal of a constraint.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        constraint_name = item['entity_name']
        constraints_dict[constraint_name] = {
            "command": f"ALTER TABLE {item['schema_name']}.{item['table_name']} DROP CONSTRAINT {constraint_name};"
        }

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
        return self.db.adapter.struct_create_index_sql(schema_name=index_item['schema_name'],
                                                       table_name = index_item['table_name'],
                                                       columns=attributes.get("columns"),
                                                       index_name=index_name,
                                                       method=attributes.get("method"),
                                                       with_options=attributes.get("with_options"),
                                                       tablespace= attributes.get("tablespace"),
                                                       where=attributes.get('where'))
        
        
    
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
                relations_commands = ',\n'.join([colitem['command'] for colitem in tbl_item['relations'].values()])

                #constraints_commands = ',\n'.join([colitem['command'] for colitem in tbl_item['constraints'].values()])
                #constrainList.append(constraints_commands)
                tbl_command = tbl_item.get('command')
                alter_table_command = f"""ALTER TABLE "{schema_name}"."{table_name}" """
                if (col_commands or relations_commands) and not tbl_command:
                    tbl_item['command'] = alter_table_command
                if col_commands:
                    commandlist.append(f"{tbl_item['command']}\n {col_commands};")
                else:
                    commandlist.append(tbl_item['command'])
                if relations_commands:
                    if col_commands and tbl_item['command']==alter_table_command:
                        commandlist.append(f"{tbl_item['command']}\n {relations_commands};")
                    else:
                        commandlist.append(relations_commands)
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
    
    app = GnrApp('dbsetup_tester')
    mig = SqlMigrator(app.db)
    mig.toSql()

    with open('testsqlextractor.json','w') as f:
        f.write(json.dumps(mig.sqlStructure))

    with open('testormextractor.json','w') as f:
        f.write(json.dumps(mig.ormStructure))

    print(mig.diff)

   #diff = compare_json({},mig.ormStructure)
   #print('\n---from 0 to 1 \n',diff)
    #diff = compare_json(mig_1.ormStructure,mig.ormStructure)
    #print('\n---from 1 to 0',diff)
    #print('orm mig1',mig_1.ormStructure)
    #mig.applyChanges()
    #print('\n'.join([c["sql"] for c in mig.commands]))