import pytest
from gnr.sql.adapters import _gnrbaseadapter as ba

class FakeCursor(object):
    def fetchall(self):
        return [(1,2)]
    
class FakeDbRoot(object):
    def __init__(self, fixed_schema):
        self.fixed_schema = fixed_schema
    def execute(self, query, p, **params):
        return FakeCursor()

class FakeConnection(object):
    def cursor(self, name="none"):
        return name

class FakeColumn(object):
    def __init__(self, attributes):
        self.attributes = attributes
    def __repr__(self):
        return ""
    def __str__(self):
        return ""
    
class FakeTableObj(object):
    pkey = "id"
    sqlfullname = "mytable"

    @property
    def sqlnamemapper(self):
        return self.columns
    
    virtual_columns = ['virtual_col1',
                       'virtual_col2']
    columns = {
        'id': FakeColumn(attributes={'sql_value': 'int'}),
        'column1': FakeColumn(attributes={'sql_value': 'int'}),
        'column2': FakeColumn(attributes={'sql_value': 'char'})
    }
    def column(self, name):
        return self.columns.get(name)
class FakeTable(object):
    model = FakeTableObj()
    fullname = "mytable"

    
class TestSqlDbAdapter():
    @classmethod
    def setup_class(cls):
        cls.adapter = ba.SqlDbAdapter(FakeDbRoot(False))
        cls.adapter_fixed_schema = ba.SqlDbAdapter(FakeDbRoot("fixed_schema"))

    def test_adapter_listing(self):
        from gnr.sql import adapters
        all_adapters = adapters.__all__
        assert len(all_adapters) == 8
        assert "gnrpostgres" in all_adapters
        assert "gnrsqlite" in all_adapters
        
    def test_basic_methods(self):
        assert self.adapter.setLocale("it_IT") is None
        assert self.adapter.adaptSqlSchema("schema_name") == "schema_name"
        assert self.adapter.adaptSqlName("schema_name") == "schema_name"
        assert self.adapter_fixed_schema.adaptSqlSchema("schema_name") == "fixed_schema"
        assert self.adapter.asTranslator('hello') == '"hello"'

    def test_extension(self):
        for m in ['createExtensionSql', 'dropExtensionSql',
                  'dropExtension', 'createExtension']:
            assert getattr(self.adapter, m)("extension payload") is None
            
    def test_cursor_getter(self):
        conn1 = FakeConnection()
        conns = [conn1, FakeConnection()]

        assert self.adapter.cursor(conn1) == "none"
        assert self.adapter.cursor(conn1, "cursor1") == "cursor1"

        assert isinstance(self.adapter.cursor(conns) , list)
        assert "none" in self.adapter.cursor(conns)

        assert isinstance(self.adapter.cursor(conns, "cursor2") , list)
        assert "cursor2" in self.adapter.cursor(conns, "cursor2")
        
        
    def test_notimplemented_methods(self):
        # all these methods should return a NotImplemented
        # exception since they need to be overridden by
        # the adapter
        cover_methods = {

            (): ['defaultMainSchema', 'relations',
                 'getTableConstraints'],
            ('arg1',): ['connect', 'listen',
                        'notify', 'createDb',
                        'dropDb', 'dump', 'restore',
                        'importRemoteDb', 'listRemoteDatabases',
                        'listElements'],
            ('arg1', 'arg2'): ['getPkey', 'getIndexesForTable'],
            ('arg1', 'arg2', 'arg3'): ['getColInfo', 'lockTable'],
        }

        for args, methods in cover_methods.items():
            for method in methods:
                with pytest.raises(ba.AdapterMethodNotImplemented):
                    getattr(self.adapter, method)(*args)


    def test_filterColInfo(self):
        valid_keys = ('name', 'sqldefault', 'notnull', 'dtype', 'position', 'length')
        test_data = {v: f"{v}_val" for v in valid_keys}
        invalid_keys = ('superhero', 'weight', 'surname')
        test_data.update({v: f"{v}_val" for v in invalid_keys})
        filtered_data = self.adapter._filterColInfo(test_data, "prefix")
        for k in valid_keys:
            assert k in filtered_data
        for k in invalid_keys:
            assert k not in filtered_data
            assert f"prefix{k}" in filtered_data

    def test_compilesql(self):
        r = self.adapter.compileSql("maintable", "a, b", joins=['a','b'],
                                    where='b=1')
        assert "FOR UPDATE" not in r
        assert "maintable" in r
        assert "a, b" in r
        assert "WHERE" in r
        r = self.adapter.compileSql("maintable", "a, b", joins=['a','b'],
                                    for_update=True,
                                    where='b=1')
        assert "maintable" in r
        assert "FOR UPDATE" in r
        assert "a, b" in r
        assert "WHERE" in r
        params = {
            "where": 'WHERE',
            "group_by": "GROUP BY",
            "having": "HAVING",
            "order_by": "ORDER BY",
            "limit": "LIMIT",
            "offset": "OFFSET"
        }
        
        for p, k in params.items():
            new_params = {p: 1}
            r = self.adapter.compileSql("maintable", "a, b", joins=['a','b'],
                                        for_update=True, **new_params)
            for p2, k2 in params.items():
                assert k in r
                if p2 != p:
                    assert k2 not in r

    def test_prepareRecordData(self):
        with pytest.raises(AttributeError):
            # the default value for tableobj params cause exception
            self.adapter.prepareRecordData([])

        r = self.adapter.prepareRecordData({"column1": 1}, FakeTableObj())
        assert r['column1']
        assert r['column2'] is None

    def test_sqltext(self):
        sql_text = "SELECT foobar FROM TABLE WHERE a = :test"
        sql_args = {}
        
        # args are always returned as-is
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        
        sql_args = {"test": [1,2,3]}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" in r[0]
        assert "test1" in r[0]

        sql_args = {"test": (1,2,3)}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" in r[0]
        assert "test1" in r[0]

        sql_args = {"test": {1,2,3}}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" in r[0]
        assert "test1" in r[0]

        sql_args = {"test": [1]}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" in r[0]

        sql_args = {"test": 1}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" not in r[0]
        
        sql_args = {"test": "ciao"}
        r = self.adapter.prepareSqlText(sql_text, sql_args)
        assert r[1] == sql_args
        assert "test0" not in r[0]
        
    def test_existrecord(self):
        r = self.adapter.existsRecord(FakeTable(), {"id":1})
        assert r is True

    def test_insert(self):
        # TBD, due to type checking errors
        #r = self.adapter.insert(FakeTable(), {"column1": "1", "column3": "2"})
        pass
        
    def test_rangetosql(self):
        r = self.adapter.rangeToSql("col", "prefix",
                                    rangeStart=10,
                                    rangeEnd=20,
                                    includeStart=True,
                                    includeEnd=True)
        assert "<=" in r
        assert ">=" in r
        
        r = self.adapter.rangeToSql("col", "prefix",
                                    rangeStart=10,
                                    rangeEnd=20,
                                    includeStart=False,
                                    includeEnd=False)
        assert "<=" not in r
        assert ">=" not in r
        r = self.adapter.rangeToSql("col", "prefix",
                                    rangeStart=True,
                                    rangeEnd=False,
                                    includeStart=False,
                                    includeEnd=False)
        assert ">" in r
        assert "<" not in r
        assert "AND" not in r

    def test_sqlfireevent(self):
        r = self.adapter.sqlFireEvent("link", "path", "col")
        assert ">link<" in r
        assert "'path'" in r
        assert "(col)" in r
        assert "<a" in r
        assert "</a>" in r

    def test_ageatdate(self):
        r = self.adapter.ageAtDate("datecol")
        assert "datecol" in r
        assert "86400" in r
        r = self.adapter.ageAtDate("datecol", timeUnit='year')
        assert "31536000" in r

    
    def test_statements(self):
        r = self.adapter.string_agg("field", "separator")
        assert "string_agg(" in r.lower()
        assert "field" in r
        assert "separator" in r

        
        r = self.adapter.addUniqueConstraint("package", "table", "field")
        assert r == "ALTER TABLE package.table ADD CONSTRAINT un_package_table_field UNIQUE (field)"

        r = self.adapter.createSchemaSql("MYSCHEMA")
        assert r == "CREATE SCHEMA MYSCHEMA;"
