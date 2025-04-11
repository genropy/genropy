import threading
import re
from collections import defaultdict
import subprocess
from gnr.core.gnrbag import Bag
from gnr.dev.decorator import time_measure
from gnr.sql import AdapterCapabilities as Capabilities
from gnr.sql.adapters._gnrbaseadapter import SqlDbAdapter as SqlDbBaseAdapter,MacroExpander as BaseMacroExpander
from gnr.sql.adapters._gnrbaseadapter import GnrWhereTranslator, DbAdapterException

DEFAULT_INDEX_METHOD = 'btree'

class MacroExpander(BaseMacroExpander):
    # Regex patterns for each macro with improved support for quoted identifiers
    
    macros = {
        'TSQUERY':re.compile(
                            r"#TSQUERY(?:_(?P<querycode>\w+))?\s*\(\s*"  # `querycode` opzionale dopo `_`
                            r"(?P<tsv>[\$\@][\w\.\@]+)\s*,\s*"  # Primo parametro: colonna
                            r"(?P<querystring>[:\$\@][\w\.\@]+)\s*"  # Secondo parametro: può iniziare con `:`, `$` o `@`
                            r"(?:,\s*(?P<language>[:\$\@][\w\.\@]+))?\s*"  # Terzo parametro (opzionale), stesso pattern del secondo
                            r"\)"
                    ),
        'TSRANK': re.compile(
            r"#TSRANK(?:_(?P<code>\w+))?"
            r"(?:\(\s*(?:\[(?P<weights>[\d.,\s]*)\])?\s*"
            r"(?:,\s*(?P<normalization>\d+))?\s*\))?"
        ),
        'TSHEADLINE': re.compile(
                r"#TSHEADLINE(?:_(?P<querycode>\w+))?\s*\(\s*"  # `querycode` opzionale dopo `_`
                r"(?P<textfield>[\$\@][\w\.\@]+)\s*"  # Primo parametro: colonna con il testo
                r"(?:,\s*'(?P<config>[^']+)')?\s*"  # Config opzionale tra apici singoli
                r"\)"
        )
    }

    def _expand_TSQUERY(self, m):
        """Expands the #TSQUERY macro into a full-text search condition using websearch_to_tsquery."""
        tsv = m.group("tsv").strip()  # The field contining the ts_vector
        querystring = m.group("querystring")  # The search text parameter (e.g., :querystring)
        language = m.group("language") or "'simple'"  # Default to 'simple' if no language is provided
        sqlparams = self.querycompiler.sqlparams
        channel_code = m.group('querycode') or 'current'
        sqlparams[f'tsquery_{channel_code}'] = {'querystring':querystring,'language':language,'tsv':tsv}
        return f"{tsv} @@ websearch_to_tsquery(CAST({language} AS regconfig),{querystring})"

    def _expand_TSRANK(self, m):
        """Expands the #TSRANK macro into a ts_rank function for ranking full-text search results."""
        weights = m.group("weights") or 'ARRAY[0.1, 0.2, 0.4, 1.0]' # The weight array
        normalization = m.group("normalization") or 8  # Default normalization factor
        channel_code = m.group('code') or 'current'
        sqlparams = self.querycompiler.sqlparams
        tsquery_params = sqlparams.get(f'tsquery_{channel_code}',{})
        query_param = tsquery_params.get("querystring",'')  # The search text parameter (e.g., :querystring)
        language_param = tsquery_params.get("language",'simple')  # Default language to 'simple'
        tsvector = tsquery_params['tsv']
        result =  f"ts_rank({tsvector}, websearch_to_tsquery(CAST({language_param} AS regconfig), {query_param}))"
        if normalization:
            result =  f"ts_rank({tsvector}, websearch_to_tsquery(CAST({language_param} AS regconfig), {query_param}),{normalization})"
        if weights:
            result =  f"ts_rank({weights},{tsvector}, websearch_to_tsquery(CAST({language_param} AS regconfig), {query_param}),{normalization})"
        return result

    def _expand_TSHEADLINE(self, m):
        """Expands the #TSHEADLINE macro into a ts_headline function for highlighting search terms."""
        text_field = m.group("textfield").strip()  # The text field to highlight
        channel_code = m.group('querycode') or 'current'
        sqlparams = self.querycompiler.sqlparams
        tsquery_params = sqlparams.get(f'tsquery_{channel_code}',{})
        if not tsquery_params:
            return "''"
        query_param = tsquery_params.get("querystring",'')  # The search text parameter (e.g., :querystring)
        language_param = tsquery_params.get("language",'simple')  # Default language to 'simple'
        config = m.group("config") or "StartSel=<mark>, StopSel=</mark>, MaxWords=20, MinWords=5, MaxFragments=99, FragmentDelimiter=<hr/>"
        return f"ts_headline(CAST({language_param} AS regconfig), {text_field}, websearch_to_tsquery(CAST({language_param} AS regconfig), {query_param}), '{config}')"



class PostgresSqlDbBaseAdapter(SqlDbBaseAdapter):
    REQUIRED_EXECUTABLES = ['psql','pg_dump', 'pg_restore']
    
    CAPABILITIES = {
        Capabilities.MIGRATIONS,
        Capabilities.VECTOR,
        Capabilities.SCHEMAS
    }
    
    _lock = threading.Lock()
    paramstyle = 'pyformat'

    typesDict = {
        'bigint': 'L', 
        'boolean': 'B',
        'bytea': 'O',
        'character varying': 'A',
        'character': 'C',
        'date': 'D',
        'double precision': 'R', 
        'integer': 'I',
        'jsonb': 'jsonb',
        'money': 'M',
        'numeric': 'N',
        'real': 'R',
        'smallint': 'I', 
        'text': 'T',
        'time with time zone': 'HZ',
        'time without time zone': 'H',
        'timestamp with time zone': 'DHZ',
        'timestamp without time zone': 'DH',
        'tsvector':'TSV',
        'vector':'VEC',
    }
    
    revTypesDict = {
        'A': 'character varying',
        'B': 'boolean',
        'C': 'character',
        'D': 'date',
        'DH': 'timestamp without time zone',
        'DHZ': 'timestamp with time zone',
        'H': 'time without time zone',
        'HZ': 'time with time zone',
        'I': 'integer',
        'L': 'bigint',
        'M': 'money',
        'N': 'numeric',
        'O': 'bytea',
        'P': 'text',
        'R': 'real',
        'T': 'text',
        'TSV':'tsvector',
        'VEC':'vector',
        'X': 'text',
        'Z': 'text',
        'jsonb':'jsonb',
        'serial': 'serial8',
    }


    @property
    def macroExpander(self):
        return MacroExpander
    
    def defaultMainSchema(self):
        return 'public'

    @classmethod
    def adaptSqlName(cls,name):
        return '"%s"' %name

    
    def setLocale(self, locale):
        """
        There is no direct way to set a locale in a connection, only
        in DDL statements
        """
        pass
    
    def lockTable(self, dbtable, mode='ACCESS EXCLUSIVE', nowait=False):
        if nowait:
            nowait = 'NO WAIT'
        else:
            nowait = ''
        sql = "LOCK %s IN %s MODE %s;" % (dbtable.model.sqlfullname, mode, nowait)
        self.dbroot.execute(sql)

    def dropTable(self, dbtable,cascade=False):
        """Drop table"""
        command = 'DROP TABLE IF EXISTS %s;'
        if cascade:
            command = 'DROP TABLE %s CASCADE;'
        tablename = dbtable if isinstance(dbtable,str) else dbtable.model.sqlfullname
        self.dbroot.execute(command % tablename)
        
    def dump(self, filename,dbname=None,excluded_schemas=None, options=None,**kwargs):
        """Dump an existing database
        :param filename: db name
        :param excluded_schemas: excluded schemas
        :param filename: dump options"""
        available_parameters = dict(
            data_only='-a', clean='-c', create='-C', no_owner='-O',
            schema_only='-s', no_privileges='-x', if_exists='--if-exists',
            quote_all_identifiers='--quote-all-identifiers',
            compress = '--compress='
        )
        dbname = dbname or self.dbroot.dbname
        pars = {'dbname':dbname,
                'user':self.dbroot.user,
                'password':self.dbroot.password,
                'host':self.dbroot.host or 'localhost',
                'port':self.dbroot.port or '5432'}
        excluded_schemas = excluded_schemas or []
        options = options or Bag()
        dump_options = []
        for excluded_schema in excluded_schemas:
            dump_options.append('-N')
            dump_options.append(excluded_schema)
        if options['plain_text']:
            dump_options.append('-Fp')
            file_extension = '.sql'
        else:
            dump_options.append('-Fc')
            file_extension = '.pgd'
        for parameter_name, parameter_label in list(available_parameters.items()):
            parameter_value = options[parameter_name]
            if parameter_value:
                if parameter_label.endswith('='):
                    parameter_value = '%s%s'%(parameter_label,parameter_value)
                else:
                    parameter_value = parameter_label
                dump_options.append(parameter_value)
        if not filename.endswith(file_extension):
            filename = '%s%s' % (filename, file_extension)
        #args = ['pg_dump', dbname, '-U', self.dbroot.user, '-f', filename]+extras
        args = ['pg_dump',
            '--dbname=postgresql://%(user)s:%(password)s@%(host)s:%(port)s/%(dbname)s' %pars, 
            '-f', filename]+dump_options
        callresult = subprocess.call(args)
        return filename

    def _managerConnection(self):
        return self._classConnection(host=self.dbroot.host, 
                                     port=self.dbroot.port,
                                     user=self.dbroot.user, 
                                     password=self.dbroot.password)

    @classmethod
    def _createDb(cls, dbname=None, host=None, port=None,
                  user=None, password=None, encoding='unicode'):
        conn = cls._classConnection(host=host, user=user,
                                    password=password, port=port)
        curs = conn.cursor()
        try:
            curs.execute(cls.createDbSql(dbname, encoding))
            conn.commit()
        except:
            raise DbAdapterException(f"Could not create database {dbname}")
        finally:
            curs.close()
            conn.close()
            curs = None
            conn = None

    @classmethod
    def createDbSql(self, dbname, encoding):
        return """CREATE DATABASE "%s" ENCODING '%s';""" % (dbname, encoding)


    def createDb(self, dbname=None, encoding='unicode'):
        if not dbname:
            dbname = self.dbroot.get_dbname()
        self._createDb(dbname=dbname, host=self.dbroot.host, port=self.dbroot.port,
                       user=self.dbroot.user, password=self.dbroot.password)

    @classmethod
    def _dropDb(cls, dbname=None, host=None, port=None,
        user=None, password=None):
        conn = cls._classConnection(host=host, user=user,
            password=password, port=port)
        curs = conn.cursor()
        curs.execute(f'DROP DATABASE IF EXISTS "{dbname}";')
        curs.close()
        conn.close()
        curs = None
        conn = None

    def dropDb(self, dbname=None):
        self._dropDb(dbname=dbname, host=self.dbroot.host, port=self.dbroot.port,
            user=self.dbroot.user, password=self.dbroot.password)

    def importRemoteDb(self, source_dbname,source_ssh_host=None,source_ssh_user=None,
                                source_dbuser=None,source_dbpassword=None,
                                source_dbhost=None,source_dbport=None,
                                dest_dbname=None):
        dest_dbname = dest_dbname or source_dbname
        self.createDb(dbname=dest_dbname, encoding='unicode')
        srcdb = dict(user=source_dbuser or 'postgres',dbname=source_dbname,
                        password=source_dbpassword or 'postgres',
                        host = source_dbhost or 'localhost',
                        port = source_dbport or '5432')
        ps = subprocess.Popen((
            'ssh','%s@%s' %(source_ssh_user,source_ssh_host),
            '-C', "pg_dump --dbname=postgresql://%(user)s:%(password)s@%(host)s:%(port)s/%(dbname)s" %srcdb
            ),stdout=subprocess.PIPE)
        destdb = {'dbname':dest_dbname,
                'user':self.dbroot.user,
                'password':self.dbroot.password,
                'host':self.dbroot.host or 'localhost',
                'port':self.dbroot.port or '5432'
                }
        output = subprocess.check_output(('psql', 
                                        'dbname=%(dbname)s user=%(user)s password=%(password)s host=%(host)s port=%(port)s' %destdb),
                                        stdin=ps.stdout)
        ps.wait()

    def listRemoteDatabases(self,source_ssh_host=None,source_ssh_user=None,
                                source_dbuser=None,source_dbpassword=None,
                                source_dbhost=None,source_dbport=None):
        srcdb = dict(user=source_dbuser or 'postgres',
                        password=source_dbpassword or 'postgres',
                        host = source_dbhost or 'localhost',
                        port = source_dbport or '5432')
        ps = subprocess.Popen((
            'ssh','%s@%s' %(source_ssh_user,source_ssh_host),
            '-C', 'psql','-l','-t', "user=%(user)s password=%(password)s host=%(host)s port=%(port)s" %srcdb
            ),stdout=subprocess.PIPE)
        res = ps.stdout.read()
        ps.wait()
        result = []
        if not res:
            return []
        for dbr in res.split('\n'):
            dbname = dbr.split('|')[0].strip()
            if dbname:
                result.append(dbname)
        return result

    def createTableAs(self, sqltable, query, sqlparams):
        self.dbroot.execute("CREATE TABLE %s WITH OIDS AS %s;" % (sqltable, query), sqlparams)


    def dbExists(self, dbname):
        conn = self._managerConnection()
        curs = conn.cursor()
        curs.execute(self._list_databases())
        dbnames = [dbn[0] for dbn in curs.fetchall()]
        curs.close()
        conn.close()
        curs = None
        conn = None
        return dbname in dbnames

    def _list_databases(self):
        return 'SELECT datname FROM pg_catalog.pg_database;'

    def _list_schemata(self):
        return """SELECT schema_name FROM information_schema.schemata 
              WHERE schema_name != 'information_schema' AND schema_name NOT LIKE 'pg_%%'"""

    def _list_tables(self):
        return """SELECT table_name FROM information_schema.tables
                                    WHERE table_schema=:schema"""

    def _list_views(self):
        return """SELECT table_name FROM information_schema.views WHERE table_schema=:schema"""

    def _list_extensions(self):
        return """SELECT name FROM pg_available_extensions;"""

    def _list_enabled_extensions(self):
        return """SELECT name FROM pg_available_extensions where installed_version IS NOT NULL;"""
    
    def _list_columns(self):
        return """SELECT column_name as col
                                  FROM information_schema.columns
                                  WHERE table_schema=:schema
                                  AND table_name=:table
                                  ORDER BY ordinal_position"""

    def dropExtension(self, extensions):
        """Disable a specific db extension"""
        extensions = extensions.split(',')
        enabled = self.listElements('enabled_extensions')
        commit = False
        for extension in extensions:
            if extension in enabled:
                self.dbroot.execute(self.dropExtensionSql(extension))
                commit = True
        return commit

    def createExtension(self, extensions):
        """Enable a specific db extension"""
        extensions = extensions.split(',')
        enabled = self.listElements('enabled_extensions')
        commit = False
        for extension in extensions:
            if not extension in enabled:
                self.dbroot.execute(self.createExtensionSql(extension))
                commit = True
        return commit

    def createExtensionSql(self,extension):
        return """CREATE extension %s;""" %extension

    def dropExtensionSql(self,extension):
        return """DROP extension IF EXISTS %s;""" %extension

    def relations(self):
        """Get a list of all relations in the db. 
        Each element of the list is a list (or tuple) with this elements:
        [foreign_constraint_name, many_schema, many_tbl, [many_col, ...], unique_constraint_name, one_schema, one_tbl, [one_col, ...]]
        @return: list of relation's details
        """
        sql = """SELECT r.constraint_name AS ref,
                c1.table_schema AS ref_schema,
                c1.table_name AS ref_tbl, 
                mcols.column_name AS ref_col,
                r.unique_constraint_name AS un_ref,
                c2.table_schema AS un_schema,
                c2.table_name AS un_tbl,
                ucols.column_name AS un_col,
                r.update_rule AS upd_rule,
                r.delete_rule AS del_rule,
                c1.initially_deferred AS init_defer
                
                FROM information_schema.referential_constraints AS r
                        JOIN information_schema.table_constraints AS c1
                                ON c1.constraint_catalog = r.constraint_catalog 
                                        AND c1.constraint_schema = r.constraint_schema
                                        AND c1.constraint_name = r.constraint_name 
                        JOIN information_schema.table_constraints AS c2
                                ON c2.constraint_catalog = r.unique_constraint_catalog 
                                        AND c2.constraint_schema = r.unique_constraint_schema
                                        AND c2.constraint_name = r.unique_constraint_name
                        JOIN information_schema.key_column_usage as mcols
                                ON mcols.constraint_schema = r.constraint_schema 
                                        AND mcols.constraint_name= r.constraint_name
                        JOIN information_schema.key_column_usage as ucols
                                ON ucols.constraint_schema = r.unique_constraint_schema
                                        AND ucols.constraint_name= r.unique_constraint_name
                                        """
        ref_constraints = self.dbroot.execute(sql).fetchall()
        ref_dict = {}
        for (
        ref, schema, tbl, col, un_ref, un_schema, un_tbl, un_col, upd_rule, del_rule, init_defer) in ref_constraints:
            r = ref_dict.get(ref, None)
            if r:
                if not col in r[3]:
                    r[3].append(col)
                if not un_col in r[7]:
                    r[7].append(un_col)
            else:
                ref_dict[ref] = [ref, schema, tbl, [col], un_ref, un_schema, un_tbl, [un_col], upd_rule, del_rule,
                                 init_defer]
        return list(ref_dict.values())

    def getPkey(self, table, schema):
        """:param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: schema name
        :return: list of columns wich are the primary key for the table"""
        sql = """SELECT k.column_name        AS col
                FROM   information_schema.key_column_usage      AS k 
                JOIN   information_schema.table_constraints     AS c
                ON     c.constraint_catalog = k.constraint_catalog 
                AND    c.constraint_schema  = k.constraint_schema
                AND    c.constraint_name    = k.constraint_name         
                WHERE  k.table_schema       =:schema
                AND    k.table_name         =:table 
                AND    c.constraint_type    ='PRIMARY KEY'
                ORDER BY k.ordinal_position"""
        return [r['col'] for r in self.dbroot.execute(sql, dict(schema=schema, table=table)).fetchall()]

    def getIndexesForTable(self, table, schema):
        """Get a (list of) dict containing details about all the indexes of a table.
        Each dict has those info: name, primary (bool), unique (bool), columns (comma separated string)

        :param table: the :ref:`database table <table>` name, in the form ``packageName.tableName``
                      (packageName is the name of the :ref:`package <packages>` to which the table
                      belongs to)
        :param schema: schema name
        :returns: list of index infos"""
        sql = """SELECT indcls.relname AS name, indisunique AS unique, indisprimary AS primary, indkey AS columns
                    FROM pg_index
               LEFT JOIN pg_class AS indcls ON indexrelid=indcls.oid
               LEFT JOIN pg_class AS tblcls ON indrelid=tblcls.oid
               LEFT JOIN pg_namespace ON pg_namespace.oid=tblcls.relnamespace
                   WHERE nspname=:schema AND tblcls.relname=:table;"""
        indexes = self.dbroot.execute(sql, dict(schema=schema, table=table)).fetchall()
        return indexes

    def getTableConstraints(self, table=None, schema=None):
        """Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        Every other info stored in information_schema.columns is available with the prefix '_pg_'"""
        sql = """SELECT constraint_type,column_name,tc.table_name,tc.table_schema,tc.constraint_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.constraint_column_usage AS cu 
                ON cu.constraint_name=tc.constraint_name  
                WHERE constraint_type='UNIQUE'
                %s%s;"""
        filtertable = ""
        if table:
            filtertable = " AND tc.table_name=:table"
        filterschema = ""
        if schema:
            filterschema = " AND tc.table_schema=:schema"
        result = self.dbroot.execute(sql % (filtertable,filterschema),
                                      dict(schema=schema,
                                           table=table)).fetchall()
            
        res_bag = Bag()
        for row in result:
            row=dict(row)
            res_bag.setItem('%(table_schema)s.%(table_name)s.%(column_name)s'%row,row['constraint_name'])
        return res_bag

    def getWhereTranslator(self):
        return GnrWhereTranslatorPG(self.dbroot)

    def struct_auto_extension_attributes(self):
        return ['unaccent']

    def struct_table_fullname_sql(self,schema_name,table_name):
        return  f'"{schema_name}"."{table_name}"'
    
    def struct_drop_table_pkey_sql(self,schema_name,table_name):
        sqltablename = self.struct_table_fullname_sql(schema_name,table_name)
        return f"ALTER TABLE {sqltablename} DROP CONSTRAINT IF EXISTS {table_name}_pkey;"

    def struct_add_table_pkey_sql(self,schema_name,table_name,pkeys):
        sqltablename = self.struct_table_fullname_sql(schema_name,table_name)
        return f'ALTER TABLE {sqltablename} ADD PRIMARY KEY ({pkeys});'

    def struct_get_schema_info_sql(self):
        return """
            SELECT
                s.schema_name,
                t.table_name,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default,
                c.numeric_precision,
                c.numeric_scale
            FROM
                information_schema.schemata s
            LEFT JOIN
                information_schema.tables t
                ON s.schema_name = t.table_schema
            LEFT JOIN
                information_schema.columns c
                ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE
                s.schema_name IN %s
            ORDER BY
                s.schema_name, t.table_name, c.ordinal_position;
        """
    
    @time_measure
    def struct_get_schema_info(self, schemas=None):
        """
        Get a (list of) dict containing details about a column or all the columns of a table.
        Each dict has those info: name, position, default, dtype, length, notnull
        Every other info stored in information_schema.columns is available with the prefix '_pg_'.
        """
        columns = self.raw_fetch(self.struct_get_schema_info_sql(), (tuple(schemas),))
    
        for schema_name, table_name, \
            column_name, data_type, \
            char_max_length, is_nullable, column_default, \
            numeric_precision, numeric_scale in columns:
            
            col = dict(
                schema_name=schema_name,
                table_name=table_name,
                name=column_name,
                dtype=data_type,
                length=char_max_length,
                is_nullable=is_nullable,
                sqldefault=column_default,
                numeric_precision=numeric_precision,
                numeric_scale=numeric_scale
            )
            col = self._filterColInfo(col, '_pg_')
            if col['sqldefault'] and col['sqldefault'].startswith('nextval('):
                col['_pg_default'] = col.pop('sqldefault')
            dtype = col['dtype'] = self.typesDict.get(col['dtype'], 'T')  # Default 'T' per tipi non riconosciuti
            if dtype == 'N':
                precision = col.pop('_pg_numeric_precision', None)
                scale = col.pop('_pg_numeric_scale', None)
                if precision is not None and scale is not None:
                    col['size'] = f"{precision},{scale}"
                elif precision is not None:  # Solo precisione
                    col['size'] = f"{precision}"
            
            # Gestione del tipo ARRAY
            elif dtype == 'A':
                size = col.pop('length', None)
                if size:
                    col['size'] = f"0:{size}"
                else:
                    dtype = col['dtype'] = 'T'  # Default a tipo sconosciuto
            
            # Gestione del tipo CHARACTER VARYING o simili
            elif dtype == 'C':
                size = col.pop('length', None)
                if size is not None:
                    col['size'] = str(size)
            
            # Gestione SERIAL
            if dtype == 'L' and col.get('_pg_default'):
                col['dtype'] = 'serial'
            
            yield col

    @time_measure
    def struct_get_constraints(self, schemas):
        """Fetch all constraints and return them in a structured dictionary."""
        constraints = defaultdict(lambda: defaultdict(dict))
        # Fetch primary key constraints
        for row in self.raw_fetch(self.get_primary_key_sql(), (schemas,)):
            schema_name, table_name, constraint_name, column_name, _ = row
            table_key = (schema_name, table_name)
            if "PRIMARY KEY" not in constraints[table_key]:
                constraints[table_key]["PRIMARY KEY"] = {
                    "constraint_name": constraint_name,
                    "constraint_type": "PRIMARY KEY",
                    "columns": []
                }
            constraints[table_key]["PRIMARY KEY"]["columns"].append(column_name)

        # Fetch unique constraints
        for row in self.raw_fetch(self.get_unique_constraint_sql(), (schemas,)):
            schema_name, table_name, constraint_name, column_name, _ = row
            table_key = (schema_name, table_name)
            if "UNIQUE" not in constraints[table_key]:
                constraints[table_key]["UNIQUE"] = {}
            if constraint_name not in constraints[table_key]["UNIQUE"]:
                constraints[table_key]["UNIQUE"][constraint_name] = {
                    "constraint_name": constraint_name,
                    "constraint_type": "UNIQUE",
                    "columns": []
                }
            constraints[table_key]["UNIQUE"][constraint_name]["columns"].append(column_name)
        
        for row in self.raw_fetch(self.get_foreign_key_sql(), (schemas,)):
            (schema_name, table_name, constraint_name, column_name,column_ord, on_update,
            on_delete, related_schema, related_table, related_column,
            deferrable, initially_deferred) = row

            table_key = (schema_name, table_name)
            if "FOREIGN KEY" not in constraints[table_key]:
                constraints[table_key]["FOREIGN KEY"] = {}
            if constraint_name not in constraints[table_key]["FOREIGN KEY"]:
                constraints[table_key]["FOREIGN KEY"][constraint_name] = {
                    "constraint_name": constraint_name,
                    "constraint_type": "FOREIGN KEY",
                    "columns": [],
                    "on_update": on_update,
                    "on_delete": on_delete,
                    "related_schema": related_schema,
                    "related_table": related_table,
                    "deferrable": deferrable == "YES",  # Convert to boolean
                    "initially_deferred": initially_deferred == "YES",  # Convert to boolean
                    "related_columns": []
                }
            constraints[table_key]["FOREIGN KEY"][constraint_name]["columns"].append(column_name)
            constraints[table_key]["FOREIGN KEY"][constraint_name]["related_columns"].append(related_column)
            
        # Fetch check constraints
        for row in self.raw_fetch(self.get_check_constraint_sql(), (schemas,)):
            schema_name, table_name, constraint_name, check_clause = row
            table_key = (schema_name, table_name)
            if "CHECK" not in constraints[table_key]:
                constraints[table_key]["CHECK"] = {}
            constraints[table_key]["CHECK"][constraint_name] = {
                "constraint_name": constraint_name,
                "constraint_type": "CHECK",
                "check_clause": check_clause
            }

        return constraints
    
    def struct_get_indexes_sql(self):
        return """
        SELECT
            n.nspname AS schema_name,               -- Schema name
            t.relname AS table_name,
            i.relname AS index_name,
            a.attname AS column_name,
            ix.indisunique AS is_unique,
            ix.indoption[array_position(ix.indkey, a.attnum)-1] & 1 AS desc_order,
            am.amname AS index_method,
            spc.spcname AS tablespace,
            pg_get_expr(ix.indpred, t.oid) AS where_clause,
            i.reloptions AS with_options,
            array_position(ix.indkey, a.attnum) AS ordinal_position,
            con.contype AS constraint_type
        FROM
            pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_am am ON i.relam = am.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_namespace n ON t.relnamespace = n.oid  -- Schema join
            LEFT JOIN pg_tablespace spc ON i.reltablespace = spc.oid
            LEFT JOIN pg_constraint con ON con.conindid = i.oid
        WHERE
            t.relkind = 'r'  -- ordinary tables only
            AND n.nspname = ANY(%s)  -- Filter by schemas
        ORDER BY
            n.nspname, t.relname, i.relname, ordinal_position;
        """
    
    @time_measure
    def struct_get_indexes(self, schemas):
        query = self.struct_get_indexes_sql()
        indexes = defaultdict(lambda: defaultdict(dict))
        for row in self.raw_fetch(query, (schemas,)):
            (schema_name, table_name, index_name, column_name, is_unique, 
            desc_order, index_method, tablespace, where_clause, 
            with_options, ordinal_position, constraint_type) = row
            
            # Key for schema and table
            table_key = (schema_name, table_name)
            
            # Init a the value if the index for table doesn't exists yet
            if index_name not in indexes[table_key]:
                indexes[table_key][index_name] = {
                    "unique": is_unique,
                    "method": index_method if index_method != DEFAULT_INDEX_METHOD else None,
                    "tablespace": tablespace,
                    "where": where_clause,
                    "with_options": {},
                    "columns": {},
                    "constraint_type": constraint_type  # p, u, etc., or None for manual indexes
                }
            
            # Aggiunge le colonne e il relativo ordinamento
            sort_order = "DESC" if desc_order else None
            indexes[table_key][index_name]["columns"][column_name] = sort_order
            
            # Parse 'with_options' and store them in the dictionary
            if with_options:
                for option in with_options:
                    k, v = option.split('=')
                    indexes[table_key][index_name]["with_options"][k.strip()] = v.strip()
        
        return indexes
    
    def struct_create_index_sql(self,schema_name=None,
                                table_name=None,
                                columns=None,index_name=None,
                                unique=None,method=None,tablespace=None,
                                with_options=None,where=None):
        with_options = with_options or {}
        method = method or "btree"
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
        where_clause = f"WHERE {where}" if where else ""
        
        # Build full table name with schema if schema is provided
        full_table_name = self.struct_table_fullname_sql(schema_name,table_name)
        
        # Compose the final SQL statement
        unique_clause = ' UNIQUE ' if unique else " "

        sql = f"""
        CREATE{unique_clause}INDEX {index_name}
        ON {full_table_name}
        USING {method} ({column_list})
        {with_clause}
        {tablespace_clause}
        {where_clause}
        """
        
        # Return a clean, single-line SQL string
        result = " ".join(sql.split())
        return f'{result};'

    def struct_is_empty_column_sql(self, schema_name=None, table_name=None, column_name=None):
        """
        Generates SQL to check if a column is empty (contains no non-NULL values).
        """
        # FIXME: since all arguments are mandatory, why default them to None and
        # check later for their presence?
        if not schema_name or not table_name or not column_name:
            raise ValueError("schema_name, table_name, and column_name are required.")
        
        return f"""
        SELECT COUNT(*) = 0 AS is_empty
        FROM "{schema_name}"."{table_name}"
        WHERE "{column_name}" IS NOT NULL;
        """

    

    def struct_alter_column_sql(self, column_name=None, new_sql_type=None,**kwargs):
        """
        Generate SQL to alter the type of a column.
        """
        return f'ALTER COLUMN "{column_name}" TYPE {new_sql_type}'

    def struct_add_not_null_sql(self, column_name,**kwargs):
        """
        Generate SQL to add a NOT NULL constraint to a column.
        """
        return f'ALTER COLUMN "{column_name}" SET NOT NULL'

    def struct_drop_not_null_sql(self, column_name,**kwargs):
        """
        Generate SQL to drop a NOT NULL constraint from a column.
        """
        return f'ALTER COLUMN "{column_name}" DROP NOT NULL'


    def struct_drop_constraint_sql(self, constraint_name, **kwargs):
        """
        Generate SQL to drop a UNIQUE constraint from a column.
        """
        return f'DROP CONSTRAINT IF EXISTS "{constraint_name}"'

    def struct_foreign_key_sql(self, fk_name, columns, related_table, related_schema, related_columns, 
                           on_delete=None, on_update=None, deferrable=False, initially_deferred=False):
        """
        Generate SQL to create a foreign key constraint.

        Parameters:
            fk_name (str): The name of the foreign key constraint.
            columns (list): List of columns in the current table.
            related_table (str): The name of the related table.
            related_schema (str): The schema of the related table.
            related_columns (list): List of columns in the related table.
            on_delete (str, optional): Action to perform on delete (e.g., CASCADE, SET NULL).
            on_update (str, optional): Action to perform on update (e.g., CASCADE, SET NULL).
            deferrable (bool, optional): Whether the constraint is deferrable (default: False).
            initially_deferred (bool, optional): Whether the constraint is initially deferred (default: False).

        Returns:
            str: The SQL string to create the foreign key constraint.
        """
        columns_str = ', '.join(f'"{col}"' for col in columns)
        related_columns_str = ', '.join(f'"{col}"' for col in related_columns)
        on_delete_str = f" ON DELETE {on_delete}" if on_delete else ""
        on_update_str = f" ON UPDATE {on_update}" if on_update else ""
        deferrable_str = " DEFERRABLE" if deferrable else ""
        initially_deferred_str = " INITIALLY DEFERRED" if deferrable and initially_deferred else ""
        
        return (
            f'CONSTRAINT "{fk_name}" FOREIGN KEY ({columns_str}) '
            f'REFERENCES "{related_schema}"."{related_table}" ({related_columns_str})'
            f'{on_delete_str}{on_update_str}{deferrable_str}{initially_deferred_str}'
        )
    
    def struct_constraint_sql(self,constraint_name=None, constraint_type=None, columns=None, check_clause=None,**kwargs):
        """
        Generate SQL to create a constraint of type UNIQUE or CHECK.
        
        Parameters:
            constraint_name (str): The name of the constraint.
            constraint_type (str): The type of constraint ('UNIQUE', 'CHECK').
            columns (list, optional): List of columns for the constraint (required for 'UNIQUE').
            check_clause (str, optional): The condition for the 'CHECK' constraint.
        
        Returns:
            str: The SQL string to create the constraint.
        """
        if constraint_type == "UNIQUE":
            if not columns:
                raise ValueError("Columns must be specified for a UNIQUE constraint.")
            columns_str = ', '.join(f'"{col}"' for col in columns)
            return f'CONSTRAINT "{constraint_name}" UNIQUE ({columns_str})'
        
        elif constraint_type == "CHECK":
            if not check_clause:
                raise ValueError("Check clause must be specified for a CHECK constraint.")
            return f'CONSTRAINT "{constraint_name}" CHECK ({check_clause})'
        
        else:
            raise ValueError(f"Unsupported constraint type: {constraint_type}")
    

    def struct_drop_table_pkey(self, schema_name, table_name):
        """
        Generate SQL to drop a primary key from a table.
        """
        return f'ALTER TABLE "{schema_name}"."{table_name}" DROP CONSTRAINT IF EXISTS "{table_name}_pkey";'

    def struct_add_table_pkey(self, schema_name, table_name, columns):
        """
        Generate SQL to add a primary key to a table.
        """
        columns_str = ', '.join(f'"{col}"' for col in columns)
        return f'ALTER TABLE "{schema_name}"."{table_name}" ADD PRIMARY KEY ({columns_str});'



    def struct_get_extensions_sql(self):
        """
        Generate the SQL code to retrieve the configured database
        extensions
        """
        return """
        SELECT 
            e.extname AS extension_name,     -- Name of the extension
            e.extversion AS version,         -- Version of the extension
            e.extrelocatable AS relocatable, -- Whether the extension is relocatable
            e.extconfig AS config_tables,    -- Configuration tables of the extension
            e.extcondition AS conditions,    -- Conditions associated with the extension
            n.nspname AS schema_name         -- Schema associated with the extension objects
        FROM 
            pg_extension e
        JOIN 
            pg_namespace n ON e.extnamespace = n.oid
        ORDER BY 
            e.extname;
        """
    @time_measure
    def struct_get_extensions(self):
        """
        Retreive the a dictionary of all available extensions
        """
        query = self.struct_get_extensions_sql()
        extensions = {}

        # Execute the query and process the results
        for row in self.raw_fetch(query, ()):
            (extension_name, version, relocatable, config_tables, conditions, schema_name) = row
            
            # Add the extension details to the dictionary
            extensions[extension_name] = {
                "version": version,
                "relocatable": relocatable,
                "config_tables": config_tables or [],
                "conditions": conditions or [],
                "schema_name": schema_name  # Schema where the extension objects are created
            }

        return extensions
    
    def struct_create_extension_sql(self, extension_name):
        """
        Generates the SQL to create an extension with optional schema, version, and cascade options.
        """
        return f"""CREATE EXTENSION IF NOT EXISTS {extension_name};"""
        


    def struct_get_event_triggers_sql(self):
        """
        Generate SQL code to retrieve all triggers
        """
        return """
        SELECT 
            evtname AS trigger_name,         -- Name of the event trigger
            evtevent AS event,              -- Event that fires the trigger (DDL command type)
            evtowner::regrole AS owner,     -- Owner of the event trigger
            obj_description(oid, 'pg_event_trigger') AS description, -- Description of the event trigger
            evtfoid::regprocedure AS function_name, -- Function invoked by the trigger
            evtenabled AS enabled_state,    -- Whether the trigger is enabled (O = enabled, D = disabled, R = replica)
            evttags AS event_tags           -- Tags for the event trigger
        FROM 
            pg_event_trigger
        ORDER BY 
            trigger_name;
        """

    @time_measure
    def struct_get_event_triggers(self):
        query = self.struct_get_event_triggers_sql()
        event_triggers = {}

        # Execute the query and process the results
        for row in self.raw_fetch(query, ()):
            (trigger_name, event, owner, description, function_name, enabled_state, event_tags) = row
            
            # Add the event trigger details to the dictionary
            event_triggers[trigger_name] = {
                "event": event,
                "owner": owner,
                "description": description,
                "function_name": function_name,
                "enabled_state": enabled_state,
                "event_tags": event_tags or []
            }

        return event_triggers

    def get_primary_key_sql(self):
        """Return the SQL query for fetching primary key constraints."""
        return """
            SELECT
                tc.constraint_schema AS schema_name,
                tc.table_name AS table_name,
                tc.constraint_name AS constraint_name,
                kcu.column_name AS column_name,
                kcu.ordinal_position AS ordinal_position
            FROM
                information_schema.table_constraints AS tc
            JOIN
                information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.constraint_schema = kcu.constraint_schema
                AND tc.table_name = kcu.table_name
            WHERE
                tc.constraint_type = 'PRIMARY KEY'
                AND tc.constraint_schema = ANY(%s)
            ORDER BY
                kcu.ordinal_position;
        """

    def get_unique_constraint_sql(self):
        """Return the SQL query for fetching unique constraints."""
        return """
            SELECT
                tc.constraint_schema AS schema_name,
                tc.table_name AS table_name,
                tc.constraint_name AS constraint_name,
                kcu.column_name AS column_name,
                kcu.ordinal_position AS ordinal_position
            FROM
                information_schema.table_constraints AS tc
            JOIN
                information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.constraint_schema = kcu.constraint_schema
                AND tc.table_name = kcu.table_name
            WHERE
                tc.constraint_type = 'UNIQUE'
                AND tc.constraint_schema = ANY(%s)
            ORDER BY
                tc.constraint_name, kcu.ordinal_position;
        """

    def get_foreign_key_sql(self):
        """Return the SQL query for fetching foreign key constraints."""
        q = """
        SELECT DISTINCT
            nsp1.nspname AS schema_name,
            cls1.relname AS table_name,
            con.conname AS constraint_name,
            att1.attname AS column_name,  
            fk.ord AS ord,
            CASE con.confupdtype
                WHEN 'a' THEN 'NO ACTION'
                WHEN 'r' THEN 'RESTRICT'
                WHEN 'c' THEN 'CASCADE'
                WHEN 'n' THEN 'SET NULL'
                WHEN 'd' THEN 'SET DEFAULT'
            END AS on_update,
            CASE con.confdeltype
                WHEN 'a' THEN 'NO ACTION'
                WHEN 'r' THEN 'RESTRICT'
                WHEN 'c' THEN 'CASCADE'
                WHEN 'n' THEN 'SET NULL'
                WHEN 'd' THEN 'SET DEFAULT'
            END AS on_delete,
            nsp2.nspname AS related_schema,
            cls2.relname AS related_table,
            att2.attname AS related_column,
            CASE con.condeferrable
                WHEN TRUE THEN 'YES'
                ELSE 'NO'
            END AS deferrable,
            CASE con.condeferred
                WHEN TRUE THEN 'YES'
                ELSE 'NO'
            END AS initially_deferred
        FROM
            pg_constraint con
        JOIN
            pg_class cls1 ON cls1.oid = con.conrelid
        JOIN
            pg_namespace nsp1 ON nsp1.oid = cls1.relnamespace
        JOIN
            LATERAL UNNEST(con.conkey) WITH ORDINALITY AS fk(colnum, ord)
            ON TRUE
        JOIN
            pg_attribute att1 ON att1.attnum = fk.colnum AND att1.attrelid = con.conrelid
        JOIN
            pg_class cls2 ON cls2.oid = con.confrelid
        JOIN
            pg_namespace nsp2 ON nsp2.oid = cls2.relnamespace
        JOIN
            LATERAL UNNEST(con.confkey) WITH ORDINALITY AS ref(colnum, ord)
            ON fk.ord = ref.ord
        JOIN
            pg_attribute att2 ON att2.attnum = ref.colnum AND att2.attrelid = con.confrelid
        WHERE
            con.contype = 'f' -- Only foreign keys
            AND nsp1.nspname = ANY(%s)
        ORDER BY
            con.conname,
            ord;"""

        return q

    
    def get_check_constraint_sql(self):
        """Return the SQL query for fetching check constraints."""
        return """
            SELECT
                tc.constraint_schema AS schema_name,
                tc.table_name AS table_name,
                tc.constraint_name AS constraint_name,
                ch.check_clause AS check_clause
            FROM
                information_schema.table_constraints AS tc
            JOIN
                information_schema.check_constraints AS ch
                ON tc.constraint_name = ch.constraint_name
                AND tc.constraint_schema = ch.constraint_schema
            WHERE
                tc.constraint_type = 'CHECK'
                AND tc.constraint_schema = ANY(%s);
        """

    def unaccentFormula(self, field):
        return 'unaccent({prefix}{field})'.format(field=field,
                                                  prefix = '' if field[0] in ('@','$') else '$')


class GnrWhereTranslatorPG(GnrWhereTranslator):
    def op_similar(self, column, value, dtype, sqlArgs,tblobj):
        "!!Similar"
        phonetic_column =  tblobj.column(column).attributes['phonetic']
        phonetic_mode = tblobj.column(column).table.column(phonetic_column).attributes['phonetic_mode']
        return '%s = %s(:%s)' % (phonetic_column, phonetic_mode, self.storeArgs(value, dtype, sqlArgs))

    def unaccent(self,v):
        return 'unaccent(%s)' %v
