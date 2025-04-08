import re
import hashlib

import json
import dictdiffer
from collections import defaultdict

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.dev.decorator import time_measure
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException,GnrSqlException


ENTITY_TREE = {
        'schemas':{
            'tables':{
                'columns':None,
                'relations':None,
                'constraints':None,
                'indexes':None,
            }
        }
}
COMPATIBLE_TYPES = {
    "A": {"T", "C", "X", "Z", "P"},              # Text-like: character, varchar, text
    "T": {"A", "C", "X", "Z", "P"},              # Text-like: text, varchar
    "C": {"A", "T", "X", "Z", "P"},              # Text-like: character, varchar
    "I": {"L", "N"},         # Integer-like: int, bigint, numeric
    "B": {"I"},                   # Boolean-like: boolean → int
    "D": {"DH", "DHZ"},                  # Date-like: date → timestamp
    "DH": {"D", "DHZ"},     # DateTime-like: timestamp → date, with/without tz
    "N": {"I", "L", "R"},         # Numeric-like: numeric → integer, bigint
    "L": {"I", "N", "R"},              # BigInt-like: bigint → int, numeric
}

COL_JSON_KEYS = ("dtype","notnull","sqldefault","size","unique","extra_sql","generated_expression")

GNR_DTYPE_CONVERTER = {'X':'T', 'Z':'T', 'P':'T'}

def new_structure_root(dbname):
    return {'root':{
            'entity':'db',
            'entity_name':dbname,
            'schemas':{},
            'extensions':{},
            'event_triggers':{}
            }
        }

def new_schema_item(schema_name):
    return {
            'entity':'schema',
            'entity_name':schema_name,
            'tables':{},
            'schema_name':schema_name,
           
        }

def new_extension_item(extension_name):
    return {
            'entity':'extension',
            'entity_name':extension_name,
            'attributes':{},
        }
def new_event_trigger_item(event_trigger_name):
    return {
            'entity':'event_trigger',
            'entity_name':event_trigger_name,
            'attributes':{},
        }

def new_table_item(schema_name,table_name):
    return {
            'entity':'table',
            'entity_name':table_name,
            "attributes":{"pkeys":None},
            "columns": {},
            "relations":{},
            "constraints": {},
            "indexes": {},
            'schema_name':schema_name,
            'table_name':table_name
        }

def new_column_item(schema_name,table_name,column_name,attributes=None):
    return {"entity":"column",
            "entity_name":column_name,
            "attributes":clean_attributes(attributes),
            "schema_name":schema_name,
            "table_name":table_name,
            "column_name":column_name}

def new_constraint_item(schema_name,table_name,columns,constraint_type,constraint_name=None):
    hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=columns,obj_type='cst')
    return {
            "entity":"constraint",
            "entity_name":hashed_entity_name,
            "attributes":{"columns":columns,
                          "constraint_name":constraint_name or hashed_entity_name,
                          "constraint_type":constraint_type},
            "schema_name":schema_name,
            "table_name":table_name,
        }

def new_relation_item(schema_name,table_name,columns,attributes=None,constraint_name=None):
    attributes['columns'] = columns
    hashed_entity_name = hashed_name(schema=schema_name,table=table_name,
                                             columns=columns,obj_type='fk')
    constraint_name = constraint_name or hashed_entity_name
    attributes['constraint_name'] = constraint_name
    return {"entity": "relation",
            "entity_name": hashed_entity_name,
            "attributes":clean_attributes(attributes),
            "schema_name": schema_name,
            "table_name": table_name}

def new_index_item(schema_name,table_name,columns,attributes=None,index_name=None):
    hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=columns,obj_type='idx')
    attributes['index_name'] = index_name or hashed_entity_name
    return {"entity": "index",
                "entity_name": hashed_entity_name,
                "attributes":clean_attributes(attributes),
                "schema_name": schema_name,
                "table_name": table_name
                }

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


def json_equal(json1, json2):
    """Confronta due JSON indipendentemente dall'ordine degli elementi."""
    json1_str = json.dumps(json1, sort_keys=True)
    json2_str = json.dumps(json2, sort_keys=True)
    return json1_str == json2_str


def json_to_tree(data,key,entity_tree=None,parent=None):
    if parent is None:
        parent = Bag()
    if not data:
        return parent
    entity_tree = entity_tree or ENTITY_TREE
    entities = data[key]
    for entity_item in entities.values():
        content = Bag()
        parent.addItem(entity_item['entity_name'],content,
                    name=entity_item['entity_name'],
                    entity=entity_item['entity'],
                    _attributes=entity_item.get('attributes',{}))
        if not entity_tree[key]:
            continue
        children_keys = list(entity_tree[key].keys())
        single_children = len(children_keys)==1
        for childname in children_keys:
            collections = content
            if not single_children:
                collections = Bag()
                content.addItem(childname,collections,name=childname)
            json_to_tree(data[key][entity_item['entity_name']],key=childname,entity_tree=entity_tree[key],parent=collections)
    return parent
       


def clean_attributes(attributes):
    return {k:v for k,v in attributes.items() if v not in (None,{},False,[],'', "NO ACTION")}
    
 
def hashed_name(schema, table, columns, obj_type='idx'):
    """
    Generate a unique name for constraints or indexes using a hash.

    Parameters:
    - schema (str): The name of the schema.
    - table (str): The name of the table.
    - columns (list): List of columns involved in the constraint or index.
    - obj_type (str): Type of object ('idx' for index, 'fk' for foreign key constraint,cst for other constraints etc.).

    Returns:
    - str: A unique name for the constraint or index.
    """
    columns_str = "_".join(columns)  
    identifier = f"{schema}_{table}_{columns_str}_{obj_type}"
    hash_suffix = hashlib.md5(identifier.encode()).hexdigest()[:8]
    return f"{obj_type}_{hash_suffix}"

class OrmExtractor:
    col_json_keys =  COL_JSON_KEYS

    def __init__(self,migrator=None, db=None,extensions=None):
        self.migrator = migrator
        self.db = db or self.migrator.db
        self.json_structure = new_structure_root(self.db.dbname)
        self.json_meta = nested_defaultdict()
        self.extensions = extensions or []
        self.schemas = self.json_structure['root']['schemas']
        self.tenant_schema_tables = {}
        self.deferred_indexes = []

    def fill_json_package(self,pkgobj):
        schema_name = pkgobj.sqlname
        self.schemas[schema_name] = new_schema_item(schema_name)
        for tblobj in pkgobj.tables.values():
            self.fill_json_table(tblobj)
            if tblobj.multi_tenant:
                self.tenant_schema_tables[tblobj.fullname] = tblobj

    def fill_json_extension(self,extension_name):
        self.json_structure['root']['extensions'][extension_name] = new_extension_item(extension_name)

    def fill_json_table(self,tblobj,tenant_schema=None):
        schema_name = tenant_schema or tblobj.pkg.sqlname
        table_name = tblobj.sqlname
        pkeys = ','.join([tblobj.column(col).sqlname for col in tblobj.pkeys]) if tblobj.pkeys else None
        table_entity = new_table_item(schema_name,table_name)
        table_entity['attributes']['pkeys'] = pkeys
        self.schemas[schema_name]['tables'][table_name] = table_entity
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj,tenant_schema=tenant_schema)
            self.fill_json_relations_and_indexes(colobj,tenant_schema=tenant_schema)

        for compositecol in tblobj.composite_columns.values():
            self.fill_json_relations_and_indexes(compositecol,tenant_schema=tenant_schema)
            self.fill_multiple_unique_constraint(compositecol,tenant_schema=tenant_schema)


    def fill_json_column(self,colobj,tenant_schema=None):
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        colattr = colobj.attributes
        for auto_ext_attribute in self.db.adapter.struct_auto_extension_attributes():
            if colattr.get(auto_ext_attribute) and auto_ext_attribute not in self.extensions:
                self.extensions.append(auto_ext_attribute)
        attributes = self.convert_colattr(colattr)
        table_json = self.schemas[schema_name]['tables'][table_name]
        column_name = colobj.sqlname
        pkeys = table_json['attributes']['pkeys']
        if pkeys and (column_name in pkeys.split(',')):
            attributes['notnull'] = '_auto_'
            attributes.pop('unique',None)
            attributes.pop('indexed',None)
        column_entity = new_column_item(schema_name,table_name,column_name,attributes=attributes)
        table_json['columns'][colobj.sqlname] = column_entity
    
    
    def fill_json_relations_and_indexes(self,colobj,tenant_schema=None):
        colattr = colobj.attributes
        joiner =  colobj.relatedColumnJoiner()
        indexed = colattr.get('indexed') or colattr.get('unique')
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        table_json = self.schemas[schema_name]['tables'][table_name]
        pkeys = table_json['attributes']['pkeys']
        is_in_pkeys =  pkeys and (colobj.name in pkeys.split(','))
        if joiner:
            indexed = indexed or True
            relation_info = self._relation_info_from_joiner(colobj,joiner,tenant_schema=tenant_schema)
            related_to_pkeys = relation_info.pop('related_to_pkeys')
            rel_colobj = relation_info.pop('rel_colobj')
            if joiner.get('foreignkey'):
                self.fill_json_relation(colobj=colobj,attributes=relation_info,tenant_schema=tenant_schema)
            if not related_to_pkeys:
                self.deferred_indexes.append({"colobj":rel_colobj,"tenant_schema":tenant_schema})
        if indexed and not is_in_pkeys:
            self.fill_json_column_index(colobj=colobj,indexed=indexed,tenant_schema=tenant_schema)


    def fill_multiple_unique_constraint(self,compositecol,tenant_schema=None):
        colattr = compositecol.attributes
        if not colattr.get('unique'):
            return
        table_name = compositecol.table.sqlname
        schema_name = tenant_schema or compositecol.table.pkg.sqlname
        table_json = self.schemas[schema_name]['tables'][table_name]
        columns = colattr.get('composed_of').split(',')
        constraint_item = new_constraint_item(schema_name,table_name,columns,'UNIQUE')
        table_json['constraints'][constraint_item['entity_name']] = constraint_item

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
            
    def _relation_info_from_joiner(self,colobj,joiner,tenant_schema=None):
        result = {camel_to_snake(k[0:-4]):self.statement_converter(v) for k,v in joiner.items() if k.endswith('_sql')}
        related_field = joiner['one_relation']
        related_table,related_column = related_field.rsplit('.',1)
        rel_tblobj = colobj.db.table(related_table)
        rel_colobj = rel_tblobj.column(related_column)
        result['related_columns'] = (rel_colobj.attributes.get('composed_of') or rel_colobj.name).split(',')
        result['related_table'] = rel_tblobj.model.sqlname
        related_schema = rel_tblobj.pkg.sqlname
        if tenant_schema and rel_tblobj.multi_tenant:
            related_schema = tenant_schema
        result['related_schema'] = related_schema
        result['deferrable'] = joiner.get('deferrable') or joiner.get('deferred')
        result['initially_deferred'] = joiner.get('initially_deferred') or joiner.get('deferred')
        result['related_to_pkeys'] = result['related_columns'] == rel_tblobj.pkeys
        result['rel_colobj'] = rel_colobj
        return result

    def fill_json_relation(self,colobj,attributes=None,tenant_schema=None):
        columns = (colobj.attributes.get('composed_of') or colobj.name).split(',')
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        hashed_entity_name = hashed_name(schema=schema_name,table=table_name,columns=columns,obj_type='fk')
        attributes['constraint_name'] = hashed_entity_name
        attributes['columns'] = columns
        attributes['constraint_type'] = "FOREIGN KEY"
        relation_item = new_relation_item(schema_name,table_name,columns,attributes=attributes)
        table_json = self.schemas[schema_name]['tables'][table_name]
        table_json["relations"][relation_item["entity_name"]] = relation_item
        
    
    def fill_json_column_index(self,colobj,indexed=None,tenant_schema=None):
        indexed =  {} if indexed is True else dict(indexed) 
        if colobj.attributes.get('unique'):
            #if there is an unique constraint the db add an automatic index
            return
        with_options = dictExtract(indexed,'with_',pop=True)
        sorting = indexed.pop('sorting',None)
        columns = (colobj.attributes.get('composed_of') or colobj.name).split(',')
        sorting = sorting.split(',') if sorting else [None] * len(columns)
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        if tenant_schema and colobj.table.multi_tenant:
            schema_name = tenant_schema
        attributes = dict(
            columns=dict(zip(columns,sorting)),
            with_options=with_options,
            **indexed
        )
        index_item = new_index_item(schema_name,table_name,columns,attributes=attributes)
        table_json = self.schemas[schema_name]['tables'][table_name]
        table_json["indexes"][index_item["entity_name"]] = index_item
       

    def convert_colattr(self,colattr):
        result =  {k:v for k,v in colattr.items() if k in self.col_json_keys and v is not None}
        size = result.pop('size',None)
        dtype = result.pop('dtype',None)
        dtype = GNR_DTYPE_CONVERTER.get(dtype,dtype)
        if size:
            if size.startswith(':'):
                size = f'0{size}'
            if ':' in size:
                dtype = 'A'
            elif ',' not in size:
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
        self.add_tenant_schemas()
        for deferred_index_kw in self.deferred_indexes:
            colobj = deferred_index_kw['colobj']
            tenant_schema = deferred_index_kw['tenant_schema']
            self.fill_json_column_index(colobj=colobj,indexed=True,tenant_schema=tenant_schema)
        for extension_name in self.extensions:
            self.fill_json_extension(extension_name)
        return self.json_structure
    
    def add_tenant_schemas(self):
        if not self.migrator:
            return
        for tenant_schema in self.migrator.tenant_schemas:
            self.schemas[tenant_schema] = new_schema_item(tenant_schema)
            for tblobj in self.tenant_schema_tables.values():
                self.fill_json_table(tblobj,tenant_schema=tenant_schema)
    
class DbExtractor(object):
    col_json_keys =  COL_JSON_KEYS
    
    def __init__(self,migrator=None, db=None):
        self.migrator = migrator
        self.db = db or self.migrator.db
        self.conn = None

    def connect(self):
        """Establishes the connection to the database."""
        self.conn = self.db.adapter.connect()

    def close_connection(self):
        """Closes the connection to the database."""
        if self.conn:
            self.conn.close()
            
    def get_json_struct(self,schemas=None):
        self.prepare_json_struct(schemas=schemas)
        return self.json_structure
    
    @time_measure
    def prepare_json_struct(self,schemas=None):
        """Generates the JSON structure of the database."""
        self.json_structure = new_structure_root(self.db.dbname)
        self.json_meta = nested_defaultdict()
        self.json_schemas = self.json_structure["root"]['schemas']  
        infodict = self.get_info_from_db(schemas=schemas)
        if infodict is False:
            self.json_structure = {}
            return
        for k,v in infodict.items():
            getattr(self,f'process_{k}')(v,schemas=schemas)
            

    def get_info_from_db(self,schemas=None):
        result = {}
        try:
            self.connect()
            if schemas:
                adapter = self.db.adapter
                result["base_structure"] = adapter.struct_get_schema_info(schemas=schemas)
                result["constraints"] = adapter.struct_get_constraints(schemas=schemas)
                result["indexes"] = adapter.struct_get_indexes(schemas=schemas)
                result['extensions'] = adapter.struct_get_extensions()
                result['event_triggers'] = adapter.struct_get_event_triggers()
        except GnrNonExistingDbException:
            result = False
        finally:
            self.close_connection()
        return result

 
    def process_base_structure(self, base_structure,schemas=None):
        """Processes schema, table, and column metadata."""

        for schema_name in schemas:
            self.json_schemas[schema_name] = None

        for c in base_structure:
            schema_name = c.pop('_pg_schema_name')
            table_name = c.pop('_pg_table_name')
            is_nullable = c.pop('_pg_is_nullable')
            column_name = c.pop('name')
            colattr = {k:v for k,v in c.items()  if k in self.col_json_keys and v is not None}
            if not self.json_schemas[schema_name]:
                self.json_schemas[schema_name] = new_schema_item(schema_name)
            if table_name and table_name not in self.json_schemas[schema_name]["tables"]:
                self.json_schemas[schema_name]["tables"][table_name] = new_table_item(schema_name,table_name)
            if column_name:
                if is_nullable=='NO':
                    colattr['notnull'] = True
                col_item = new_column_item(schema_name,table_name,column_name,attributes=colattr)
                self.json_schemas[schema_name]["tables"][table_name]["columns"][column_name] = col_item
        
        for schema_name in schemas:
            if not self.json_schemas[schema_name]:
                self.json_schemas.pop(schema_name)

    def process_constraints(self,constraints_dict,schemas=None):
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
                    if columns[0] == table_json['attributes']['pkeys']:
                        continue
                    multiple_unique.pop(k)
                    self.json_schemas[schema_name]["tables"][table_name]['columns'][columns[0]]['attributes']['unique'] = True
            self.process_table_relations(schema_name,table_name,d.pop('FOREIGN KEY',{}))
            for multiple_unique_const in multiple_unique.values():
                const_item = new_constraint_item(schema_name,table_name,multiple_unique_const['columns'],
                                    constraint_type='UNIQUE',
                                    constraint_name= v['constraint_name'])
                table_json['constraints'][const_item['entity_name']] = const_item
            #we do not handle CHECK constraints
            

    def process_table_relations(self,schema_name,table_name,foreign_keys_dict):
        relations = self.json_schemas[schema_name]["tables"][table_name]['relations']
        for entity_attributes in foreign_keys_dict.values():
            constraint_name = entity_attributes.pop('constraint_name',None)
            relation_item = new_relation_item(schema_name,table_name,columns=entity_attributes['columns'],
                                              attributes=entity_attributes,
                                              constraint_name=constraint_name)
            relations[relation_item['entity_name']] = relation_item
            

    def process_indexes(self,indexes_dict,schemas=None):
        for tablepath,index_dict in indexes_dict.items():
            schema_name,table_name  = tablepath
            d = dict(index_dict)
            table_json = self.json_schemas[schema_name]["tables"][table_name]
            for index_name,index_attributes in d.items():
                if index_attributes.get('constraint_type'):
                    continue
                indexed_columns = list(index_attributes['columns'].keys())
                index_item = new_index_item(schema_name,table_name,columns=indexed_columns,
                                            attributes=index_attributes,
                                            index_name=index_name)
                table_json['indexes'][index_item['entity_name']] = index_item


    def process_extensions(self,extensions,**kwargs):
        for extension_name,extension_dict in extensions.items():
            if extension_dict.get('schema_name') == 'pg_catalog':
                continue
            extension_dict = clean_attributes(extension_dict)
            extension_item = new_extension_item(extension_name)
            self.json_meta['root']['extension'] = extension_dict
            self.json_structure["root"]['extensions'][extension_name] = extension_item 

    def process_event_triggers(self,event_triggers,**kwargs):
        for event_trigger_name,event_trigger_dict in event_triggers.items():
            event_trigger_item = new_event_trigger_item(event_trigger_name)
            event_trigger_item['attributes'].update(event_trigger_dict)
            self.json_structure["root"]['event_triggers'][event_trigger_name] = event_trigger_item 

class SqlMigrator():
    def __init__(self,db,
                 extensions=None,
                 ignore_constraint_name=True,
                 excludeReadOnly=True,
                 removeDisabled=True):
        self.db = db
        self.extensions = extensions.split(',') if extensions else []
        self.sql_commands = {'db_creation':None,'build_commands':None,'extensions_commands':None}
        self.dbExtractor = DbExtractor(migrator=self)
        self.ormExtractor = OrmExtractor(migrator=self,extensions=self.extensions)
        self.excludeReadOnly = excludeReadOnly
        self.removeDisabled = removeDisabled
        self.ignore_constraint_name = ignore_constraint_name
    
    @property
    def diff(self):
        return dictdiffer.diff(self.sqlStructure or {'root':{}},self.ormStructure)

    def dictDifferChanges(self):
        for diffevent, path, difflist in self.diff: 
            if isinstance(path,list):
                pathlist = path
            else:
                pathlist = path.split('.') if path else []
            attributes_index = self.get_attributes_index_in_path(pathlist)
            if attributes_index>0:
                kw = {}
                item = self.get_item_from_pathlist(self.ormStructure,pathlist[:attributes_index])
                old_attributes = self.get_item_from_pathlist(self.sqlStructure,pathlist[:attributes_index])['attributes']
                new_attributes  = item['attributes']
                changed_attributes = []
                if diffevent in ('add','remove') and pathlist[-1]=='attributes':
                    changed_attributes = [k for k,v in difflist if v!='_auto_']
                else:
                    changed_attributes = [pathlist[attributes_index+1]]
                for changed_attribute in changed_attributes:
                    kw['item'] = item
                    kw['changed_attribute'] = changed_attribute
                    kw['oldvalue'] = old_attributes.get(changed_attribute)
                    kw['newvalue'] = new_attributes.get(changed_attribute)
                    kw['entity'] = item['entity']
                    kw['entity_name'] = item['entity_name']
                    yield 'changed',kw
            else:
                collection = dict(difflist)
                if collection.get('entity_name'):
                    collection = {collection['entity_name']:collection}
                for item in collection.values():
                    kw = {}
                    kw['item'] = item
                    kw['entity'] = item['entity']
                    kw['entity_name'] = item['entity_name']
                    yield 'added' if diffevent=='add' else 'removed',kw
        

    def get_item_from_pathlist(self,d,pathlist):
        if isinstance(pathlist,str):
            pathlist = [pathlist]
        for p in pathlist:
            d = d[p]
        return d
                

    def get_attributes_index_in_path(self,pathlist):
        if 'attributes' in pathlist:
            return pathlist.index('attributes')  # Find the index of 'attributes'
        return -1


    def prepareMigrationCommands(self):
        self.prepareStructures()
        self.commands = nested_defaultdict()

        for evt,kw in self.dictDifferChanges():
            if evt=='removed' and self.removeDisabled:
                continue
            item = kw['item']
            if item.get('schema_name') in self.readOnly_schemas:
                continue
            handler = getattr(self, f'{evt}_{kw["entity"]}' ,self.missing_handler_cb)
            handler(**kw)

    def missing_handler_cb(self,**kwargs):
        return f'missing {kwargs}'
 
    def prepareStructures(self):
        self.application_schemas = self.db.getApplicationSchemas()
        self.readOnly_schemas = self.db.readOnlySchemas()
        if self.excludeReadOnly:
            self.application_schemas = [schema for schema in self.application_schemas if schema not in self.readOnly_schemas]
        try:
            self.tenant_schemas = self.db.getTenantSchemas()
        except GnrNonExistingDbException:
            self.tenant_schemas = []
        self.extractOrm()
        self.extractSql(schemas=self.application_schemas+self.tenant_schemas)

    def extractSql(self,schemas=None):
        self.sqlStructure = self.dbExtractor.get_json_struct(schemas=schemas)
    
    def extractOrm(self):
        self.ormStructure = self.ormExtractor.get_json_struct()
    
    def clearSql(self):
        self.sqlStructure = {}

    def clearOrm(self):
        self.ormStructure = {}

    def getDiffBag(self):
        result = Bag()
        for reason,kw in self.dictDifferChanges():
            diff_entity_item = kw['item'] 
            pathlist = []
            if diff_entity_item.get('schema_name'):
                pathlist.append(diff_entity_item['schema_name'])
            if diff_entity_item.get('table_name'):
                pathlist.append(diff_entity_item['table_name'])
            if diff_entity_item.get('column_name'):
                pathlist.append(diff_entity_item['column_name'])
            pathlist.append(f"{diff_entity_item['entity']}_{diff_entity_item['entity_name']}")
            pathlist.append(reason)
            entity_node = result.getNode('.'.join(pathlist),autocreate=True)
            entity_node.attr[diff_entity_item['entity']] = diff_entity_item['entity_name']
            entity_node.attr[reason] = kw
        return result


    def jsonModelWithoutMeta(self,keys_to_remove=None):
        if not (self.sqlStructure or self.ormStructure):
            self.prepareStructures()
        result = Bag()
        result.addItem('orm',json_to_tree(self.ormStructure.get('root'),key='schemas'))
        result.addItem('sql',json_to_tree(self.sqlStructure.get('root'),key='schemas'))
        return result
    
    def clearCommands(self):
        self.commands.pop('db',None) #rebuils
        
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
        if not item['columns']:
            #without columns avoid table creation
            return
        for col in item['columns'].values():
            substatements.append(self.columnSql(col).strip())
        if item["attributes"]["pkeys"]:
            substatements.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')
        for const_item in item['constraints'].values():  
            constattr = const_item['attributes']
            const_sql = self.db.adapter.struct_constraint_sql(
                const_item['entity_name'], constattr['constraint_type'],
                  columns=constattr.get('columns'), 
                  check_clause=constattr.get('check_clause')
            )
            substatements.append(const_sql)
        joined_substatements = ',\n '.join(substatements)
        sql = f"CREATE TABLE {sqltablename}(\n {joined_substatements}\n);"
        self.schema_tables(item['schema_name'])[item['table_name']]['command'] = sql
        for index_item in item['indexes'].values():
            self.added_index(item=index_item)
        for rel_item in item['relations'].values():
            self.added_relation(item=rel_item)

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
        relattr = item['attributes']
        sql =  self.db.adapter.struct_foreign_key_sql(
                fk_name=item['entity_name'],
                columns=item['attributes']['columns'],
                related_table = relattr['related_table'],
                related_schema = relattr['related_schema'],
                related_columns = relattr['related_columns'],
                on_delete = relattr.get('on_delete'),
                on_update = relattr.get('on_update'),
                deferrable= relattr.get('deferrable'),
                initially_deferred = relattr.get('initially_deferred')
            )
        
        
        relations_dict[item['entity_name']] = {
            "command":f'ADD {sql}'
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

    def added_extension(self,item=None,**kwargs):
        self.commands['db']['extensions'][item['entity_name']]['command'] = self.db.adapter.struct_create_extension_sql(
                extension_name=item['entity_name']
            )

    def added_event_trigger(self,item=None,**kwargs):
        pass


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

    def is_empty_column(self,item):
        return self.db.adapter.struct_is_empty_column(schema_name=item['schema_name'],table_name=item['table_name'],column_name=item['column_name'])

    def changed_column(self, item=None, changed_attribute=None, oldvalue=None, newvalue=None, **kwargs):
        """
        *autogenerated*
        Handle changes to a column's attributes (e.g., size, dtype, notnull, unique).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns']
        column_name = item['entity_name']
        if changed_attribute=='size' and not item.get('_rebuilt'):
            new_sql_type = self.db.adapter.columnSqlType(dtype=item['attributes']['dtype'], size=item['attributes'].get('size'))
            columns_dict[column_name]['command'] = self.db.adapter.struct_alter_column_sql(
                    column_name=column_name,
                    new_sql_type=new_sql_type,
                    schema_name=item['schema_name'],
                    table_name=item['table_name']
                )

        elif changed_attribute == 'dtype':
            compatible_types = COMPATIBLE_TYPES.get(oldvalue,[])
            if newvalue in compatible_types:
                new_sql_type = self.db.adapter.columnSqlType(dtype=item['attributes']['dtype'], size=item['attributes'].get('size'))
                columns_dict[column_name]['command'] = self.db.adapter.struct_alter_column_sql(
                    column_name=column_name,
                    new_sql_type=new_sql_type,
                    schema_name=item['schema_name'],
                    table_name=item['table_name']
                )
            else:
                if self.is_empty_column(item):
                    entity_name = item['entity_name']
                    table_dict['columns'][f'rem_{entity_name}']['command'] = f'DROP COLUMN "{entity_name}"'
                    self.added_column(item)
                    item['_rebuilt'] = True
                else:
                    raise GnrSqlException(f'Incompatible data type change in a non-empty column. Column {item["table_name"]}.{item["column_name"]} {oldvalue} {newvalue}') 
        elif changed_attribute == 'notnull':
            # Handle changes to the NOT NULL constraint
            if newvalue:
                columns_dict[column_name]['command'] = self.db.adapter.struct_add_not_null_sql(
                    column_name=column_name,
                    schema_name=item['schema_name'],
                    table_name=item['table_name']
                )
            else:
                columns_dict[column_name]['command'] = self.db.adapter.struct_drop_not_null_sql(
                    column_name=column_name,
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                )
        elif changed_attribute == 'unique':
            # Handle changes to the UNIQUE constraint
            if newvalue:
                self.addColumnUniqueConstraint(item)
            else:
                columns = [column_name]
                constraints_dict = table_dict['constraints']
                constraint_name = hashed_name(schema=item['schema_name'],table=item['table_name'],columns=columns,obj_type='cst')
                sql = self.db.adapter.struct_drop_constraint_sql(
                    constraint_name=constraint_name,
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                )
                constraints_dict[constraint_name] = {"command":sql}
        elif changed_attribute in ('generated_expression','extra_sql'):
            return

    def addColumnUniqueConstraint(self,col):
        table_dict = self.schema_tables(col['schema_name'])[col['table_name']]
        columns = [col['entity_name']]
        constraint_name = hashed_name(schema=col['schema_name'],table=col['table_name'],columns=columns,obj_type='cst')
        sql = self.db.adapter.struct_constraint_sql(
            constraint_type='UNIQUE',
            constraint_name=constraint_name,
            columns=columns,
            schema_name=col['schema_name'],
            table_name=col['table_name']
        )
        constraints_dict = table_dict['constraints']
        constraints_dict[constraint_name] = {
            "command": f'ADD {sql}'
        }

    def changed_index(self, item=None,changed_attribute=None,oldvalue=None,newvalue=None, **kwargs):
        """
        Handle changes to an index.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes']
        entity_name = item['entity_name']
        index_attributes = item['attributes']
        if changed_attribute=='index_name':
            if self.ignore_constraint_name:
                index_attributes['index_name'] = oldvalue
                return
            else:
                sql = f"ALTER INDEX {oldvalue} RENAME TO {newvalue};"
        else:
            new_command = self.createIndexSql(item)
            sql = f'DROP INDEX IF EXISTS {index_attributes["index_name"]};\n{new_command}'
        indexes_dict[entity_name]['command'] = sql

    def changed_relation(self, item=None, changed_attribute=None,oldvalue=None,newvalue=None,**kwargs):
        """
        *autogenerated*
        Handle changes to a relation (foreign key).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        entity_name = item['entity_name']
        relattr = item['attributes']
        if changed_attribute=='constraint_name':
            if self.ignore_constraint_name:
                relattr['constraint_name'] = oldvalue
            else:
                relations_dict[f'rem_{entity_name}']['command'] = f"RENAME CONSTRAINT {oldvalue} TO {newvalue};"
            return
        add_sql = self.db.adapter.struct_foreign_key_sql(
            fk_name=relattr['constraint_name'],
            columns=relattr['columns'],
            related_table=relattr['related_table'],
            related_schema=relattr['related_schema'],
            related_columns=relattr['related_columns'],
            on_delete=relattr.get('on_delete'),
            on_update=relattr.get('on_update'),
            deferrable= relattr.get('deferrable'),
            initially_deferred = relattr.get('initially_deferred')
        )
        relations_dict[f'rem_{entity_name}']['command'] = f"DROP CONSTRAINT {relattr['constraint_name']}"
        relations_dict[f'add_{entity_name}']['command'] = f"ADD {add_sql}"

    def changed_constraint(self, item=None,changed_attribute=None,oldvalue=None,newvalue=None, **kwargs):
        """
        *autogenerated*
        Handle changes to a constraint.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        entity_name = item['entity_name']
        constraint_attr = item['attributes']
        
        if changed_attribute=='constraint_name':
            if self.ignore_constraint_name:
                constraint_attr['constraint_name'] = oldvalue
            else:
                constraints_dict[f'rem_{entity_name}']['command'] = f"RENAME CONSTRAINT {oldvalue} TO {newvalue};"
            return
        add_sql = self.db.adapter.struct_constraint_sql(
                schema_name=item['schema_name'],
                table_name=item['table_name'],
                constraint_name=constraints_dict['constraint_name'],
                constraint_type=item['attributes']['constraint_type'],
                columns=item['attributes']['columns']
        )
        constraints_dict[f'drop_{entity_name}']['command'] = f"DROP CONSTRAINT {constraint_attr['constraint_name']};"
        constraints_dict[f'add_{entity_name}']['command'] = f"ADD {add_sql}"

    def removed_table(self,item=None,**kwargs):
        pass

    def removed_column(self,item=None,**kwargs):
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        entity_name = item['entity_name']
        table_dict['columns'][entity_name]['command'] = f'DROP COLUMN "{entity_name}"'


    def removed_index(self,item=None,**kwargs):
        pass

    def removed_relation(self,item=None,**kwargs):
        pass

    def removed_constraint(self,item=None,**kwargs):
        pass



    def removed_extension(self,item=None,**kwargs):
        pass

    def removed_event_trigger(self,item=None,**kwargs):
        pass

    def missing_handler(self,**kwargs):
        return f'missing {kwargs}'


    def columnSql(self, col):
        """Return the statement string for creating a table's column"""
        colattr = col['attributes']
        if colattr.get('unique'):
            self.addColumnUniqueConstraint(col)
        return self.db.adapter.columnSqlDefinition(col['entity_name'],
                                                   dtype=colattr['dtype'], size=colattr.get('size'),
                                                   notnull=colattr.get('notnull', False),
                                                    default=colattr.get('sqldefault'),
                                                    extra_sql=colattr.get('extra_sql'),
                                                    generated_expression=colattr.get('generated_expression'))
    
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
                                                       unique=attributes.get('unique'),
                                                       where=attributes.get('where'))
        
        
    def tableSqlName(self,item=None):
        schema_name = item['schema_name']
        table_name = item['table_name'] 
        return f'{self.db.adapter.adaptSqlName(schema_name)}.{self.db.adapter.adaptSqlName(table_name)}'

    def getChanges(self):
        """
        Builds and returns the SQL commands needed to apply changes to the database schema.
        
        This method processes the commands defined in `self.commands`, including:
        - Database creation commands
        - Schema-level commands
        - Table creation and modification commands (columns, indexes, constraints)
        - Relationship commands (foreign keys)

        The resulting SQL commands are stored in `self.sql_commands` and returned as a single concatenated string.
        """
        commands = self.commands
        dbitem = commands['db']
        sql_command = dbitem.get('command')
        schemas = dbitem.get('schemas', {})
        extensions_sql_commands = [extension['command'] for extension in dbitem['extensions'].values()]

        # Store database creation command
        if sql_command:
            self.sql_commands['db_creation'] = sql_command
        if extensions_sql_commands:
            self.sql_commands['extensions_commands'] = '\n'.join(extensions_sql_commands)
        command_list = []
        relation_command_list = []

        # Process each schema
        for schema_name, schema_item in schemas.items():
            schema_command = schema_item.get('command')
            tables = schema_item.get('tables', {})

            # Add schema-level command
            if schema_command:
                command_list.append(schema_command)

            # Process each table in the schema
            for table_name, tbl_item in tables.items():
                table_commands = self.sqlCommandsForTable(schema_name=schema_name,table_name=table_name,tbl_item=tbl_item)
                command_list += table_commands['commands']
                relation_command_list += table_commands['relation_commands']
        
        # Combine all commands
        command_list += relation_command_list
        self.sql_commands['build_commands'] = '\n'.join(command_list)
        # Return all SQL commands as a single string
        return '\n'.join([v for v in self.sql_commands.values() if v])
    
    def sqlCommandsForTable(self,schema_name=None,table_name=None,tbl_item=None):
        command_list = []
        relation_command_list = []
        alter_table_command = f'ALTER TABLE "{schema_name}"."{table_name}"'
        col_commands = ',\n'.join(col['command'] for col in tbl_item['columns'].values())
        constraint_commands = [con['command'] for con in tbl_item['constraints'].values()]
        
        #append to relation_command_list the foreign key constraints.
        relation_command_list += [f"{alter_table_command}\n {rel['command']};" for rel in tbl_item['relations'].values()]

        table_command = tbl_item.get('command')
        if table_command:
            command_list.append(table_command)
        # Add column commands
        elif col_commands:
            command_list.append(f"{alter_table_command}\n{col_commands};")
        # Add constraint commands
        for constraint_sql in constraint_commands:
            #if the table has been created each constraint needs an alter table 
            command_list.append(f"{alter_table_command}\n{constraint_sql};")

        # Add index commands
        command_list+=[idx['command'] for idx in tbl_item['indexes'].values()]
        return {"commands":command_list,"relation_commands":relation_command_list}

    def applyChanges(self):
        self.getChanges()
        db_creation = self.sql_commands.pop('db_creation',None)
        if db_creation:
            self.db.adapter.execute(db_creation,manager=True)
        extensions_commands = self.sql_commands.pop('extensions_commands',None)
        if extensions_commands:
            self.db.adapter.execute(extensions_commands,manager=True)
        build_commands = self.sql_commands.pop('build_commands',None)
        if build_commands:
            # FIXME: why the manager is not used in this case?
            self.db.adapter.execute(build_commands,autoCommit=True)
        


    #jsonorm = OrmExtractor(GnrApp('dbsetup_tester').db).get_json_struct()
    
def dbsetupComparison():
    app = GnrApp('sandboxpg')
    mig = SqlMigrator(app.db)
    mig.prepareMigrationCommands()

    with open('testsqlextractor.json','w') as f:
        f.write(json.dumps(mig.sqlStructure))

    with open('testormextractor.json','w') as f:
        f.write(json.dumps(mig.ormStructure))
    with open('sandbox_migration.sql','w') as f:
        f.write(mig.getChanges())

    app.db.model.check()

    with open('sandbox_modelchecker.sql','w') as f:
        f.write('\n'.join(app.db.model.modelChanges))

def multiTenantTester():
    app = GnrApp('mtx_tester')
    mig = SqlMigrator(app.db)
    mig.prepareMigrationCommands()
    with open('ts2_multi_tenant_orm.json','w') as f:
        f.write(json.dumps(mig.ormStructure))

    with open('ts2_multi_tenant_sql.json','w') as f:
        f.write(json.dumps(mig.sqlStructure))

def testTree():
    app = GnrApp('sandboxpg')
    mig = SqlMigrator(app.db)
    mig.prepareMigrationCommands()
    res = mig.jsonModelWithoutMeta()
    
if __name__ == '__main__':
    app = GnrApp('sandboxpg')
    mig = SqlMigrator(app.db)
    mig.prepareMigrationCommands()
    #testTree()
    #multiTenantTester()
