import os
import datetime

import pytest
from gnr.core import gnrlist as gl
from gnr.core import flatfiles as ff

def test_findByAttr():
    class MockObj(object):
        pass

    a = MockObj()
    a.name = "colin"
    a.surname = "adams"

    b = MockObj()
    b.name = "eddie"
    b.surname = "adams"
    
    c = MockObj()
    c.name = "arthur"
    c.surname = "dent"

    items = [a,b,c]
    assert a in gl.findByAttr(items, name="colin")
    assert b in gl.findByAttr(items, name="eddie")
    assert c in gl.findByAttr(items, name="arthur")
    assert a in gl.findByAttr(items, name="colin", surname="adams")
    assert b not in gl.findByAttr(items, name="colin", surname="adams")
    assert gl.findByAttr(items, surname="adams") == [a,b]
    assert not gl.findByAttr(items, name="ford")
    
def test_merge():
    merged = gl.merge("foobar", "goober")
    assert merged.count("o") == 2
    assert merged.count("b") == 1
    assert merged.count("e") == 1
    assert merged.count("r") == 1
    

def test_GnrNamedList():
    gnl = gl.GnrNamedList(dict(name=0, surname=1),
                          ["Arthur", "Dent"])

    assert gnl['name'] == "Arthur"
    assert gnl.keys() == ['name','surname']
    for x in gnl.iteritems():
        assert x[0] in ("name", "surname")
        assert x[1] in ("Arthur", "Dent")

    i = gnl.items()
    assert ('name', 'Arthur') in i
    assert ('surname', 'Dent') in i
    assert ('name', 'Ford') not in i
    assert ('surname', 'Prefect') not in i

    assert "name" in gnl
    assert "surname" in gnl
    assert "planet" not in gnl
    
    assert gnl.has_key("name")
    assert gnl.has_key("surname")
    assert not gnl.has_key("planet")

    assert gnl.get("name") == "Arthur"
    assert gnl.get("planet", "Earth") == "Earth"

    assert "name=" in str(gnl)
    assert "surname=" in str(gnl)
    assert "name=" in repr(gnl)
    assert "surname=" in repr(gnl)


    gnl['planet'] = "Earth"
    assert gnl.get('planet') == "Earth"
    
        
    with pytest.raises(IndexError) as excinfo:
        gnl[12] = "goober"
    assert str(excinfo.value) == "list assignment index out of range"

    with pytest.raises(IndexError) as excinfo:
        gnl[122]
    assert str(excinfo.value) == "list index out of range"


    gnl = gl.GnrNamedList(dict(name=0, surname=1))


def test_sortByItem():
    test_l = [
        dict(name="name1",
             surname="surname4",
             age=100,
             company=None,
             birth=datetime.date(2023,3,28)
             ),
        dict(name="name3",
             surname="surname3",
             age=30,
             company=dict(name="ACME, Inc.", address="Via Lemani Dalnaso"),
             birth=datetime.date(2004,3,28)
             ),
        dict(name="name2",
             surname="surname2",
             age=None,
             company={"name":"Wayne Enterprises",
                      "address": {"city":"Gotham"} },
             birth=datetime.date(2004,1,18)
             ),
        dict(name="name2",
             surname="surname1",
             age=20,
             company=None,
             birth=datetime.date(2024,3,28)
             ),
    ]

    res = gl.sortByItem(test_l)

    assert res == test_l
        
    res = gl.sortByItem(test_l, "name:*", hkeys=True)
    assert res[-1]['name'] == "name3"
    res = gl.sortByItem(test_l, "name:d", hkeys=True)
    assert res[-1]['name'] == "name1"
    res = gl.sortByItem(test_l, "name:a", hkeys=True)
    assert res[0]['name'] == "name1"
    res = gl.sortByItem(test_l, "name:a", "surname:d", hkeys=True)
    
    assert res[1]['name'] == res[2]['name'] == 'name2'
    assert res[1]['surname'] == "surname2"
    assert res[2]['surname'] == "surname1"
    res = gl.sortByItem(test_l, "name:a", "surname:a", hkeys=True)
    assert res[1]['name'] == res[2]['name'] == 'name2'
    assert res[1]['surname'] == "surname1"
    assert res[2]['surname'] == "surname2"
    res = gl.sortByItem(test_l, "age")
    assert res[-1]['age'] == 100
    res = gl.sortByItem(test_l, "age:d")
    assert res[0]['age'] == 100

    with pytest.raises(Exception):
        # we can't sort values as dict
        res = gl.sortByItem(test_l, "company", hkeys=True)

    res = gl.sortByItem(test_l, "birth", hkeys=True)
    assert res[0]['name'] == 'name2'
    assert res[0]['birth'] == datetime.date(2004,1,18)
    
    res = gl.sortByItem(test_l, "company.address.city", hkeys=True)
    assert "Wayne" in res[0]['company']['name']

    res = gl.sortByItem(test_l, "company.name:d", hkeys=True)
    assert "Wayne" in res[-1]['company']['name']
    res = gl.sortByItem(test_l, "company.name:d*", hkeys=True)
    assert "Wayne" in res[0]['company']['name']
def test_sortByAttr():
    class MockObj(object):
        a = 1

    m1 = MockObj()
    m2 = MockObj()
    m2.a = 2
    m3 = MockObj()
    m3.a = 3
    test_l = [m1, m2, m3]
    r = gl.sortByAttr(test_l, "a")

    m1 = MockObj()
    m1.a = MockObj()
    m2 = MockObj()
    m2.a = MockObj()

def test_hGetAttr():
    """Test hierarchical attribute getter"""
    class MockObj:
        def __init__(self):
            self.name = "Alice"
            self.profile = None

    class Profile:
        def __init__(self):
            self.city = "NYC"

    obj = MockObj()
    obj.profile = Profile()

    # Simple attribute
    assert gl.hGetAttr(obj, 'name') == "Alice"

    # Hierarchical attribute
    assert gl.hGetAttr(obj, 'profile.city') == "NYC"

    # Non-existent attribute
    assert gl.hGetAttr(obj, 'nonexistent') is None

    # None object
    assert gl.hGetAttr(None, 'anything') is None

    # Nested None
    obj.profile = None
    assert gl.hGetAttr(obj, 'profile.city') is None


def test_GnrNamedList_extractMethods():
    """Test extractItems and extractValues methods"""
    index = {'name': 0, 'age': 1, 'city': 2}
    row = gl.GnrNamedList(index, ['Alice', 30, 'NYC'])

    # extractItems with specific columns
    items = row.extractItems(['name', 'city'])
    assert items == [('name', 'Alice'), ('city', 'NYC')]

    # extractItems with all columns
    all_items = row.extractItems(None)
    assert len(all_items) == 3
    assert ('name', 'Alice') in all_items

    # extractValues with specific columns
    values = row.extractValues(['age', 'name'])
    assert values == [30, 'Alice']

    # extractValues with all columns
    all_values = row.extractValues(None)
    assert len(all_values) == 3
    assert 'Alice' in all_values


def test_GnrNamedList_dynamic_columns():
    """Test dynamic column addition"""
    index = {'name': 0, 'age': 1}
    row = gl.GnrNamedList(index, ['Alice', 30])

    # Add new column
    row['city'] = 'NYC'
    assert row['city'] == 'NYC'
    assert 'city' in row
    assert row._index['city'] == 2

    # Update existing column
    row['age'] = 31
    assert row['age'] == 31

    # Add another new column
    row['country'] = 'USA'
    assert row['country'] == 'USA'
    assert len(row._index) == 4



def test_GnrNamedList_iteritems():
    """Test iteritems method"""
    index = {'name': 0, 'age': 1, 'city': 2}
    row = gl.GnrNamedList(index, ['Alice', 30, 'NYC'])

    items_list = list(row.iteritems())
    assert len(items_list) == 3
    assert ('name', 'Alice') in items_list
    assert ('age', 30) in items_list
    assert ('city', 'NYC') in items_list


def test_GnrNamedList_values():
    """Test values method"""
    index = {'name': 0, 'age': 1}
    row = gl.GnrNamedList(index, ['Alice', 30])

    values = row.values()
    assert isinstance(values, tuple)
    assert len(values) == 2
    assert 'Alice' in values
    assert 30 in values


def test_sortByItem_case_insensitive():
    """Test case-insensitive sorting"""
    test_l = [
        {'name': 'alice', 'age': 30},
        {'name': 'Charlie', 'age': 25},
        {'name': 'bob', 'age': 35},
    ]

    # Case-insensitive sort
    result = gl.sortByItem(test_l, 'name:a*')
    assert result[0]['name'] == 'alice'
    assert result[1]['name'] == 'bob'
    assert result[2]['name'] == 'Charlie'


def test_GnrNamedList_sql_adapter_compatibility():
    """Test GnrNamedList works correctly when used by SQL adapter (gnrdict_row)"""
    # Simulate how gnrdict_row creates GnrNamedList
    index = {'id': 0, 'name': 1, 'email': 2}
    values = [1, 'John Doe', 'john@example.com']

    row = gl.GnrNamedList(index, values=values)

    # Test numeric access (as list)
    assert row[0] == 1
    assert row[1] == 'John Doe'
    assert row[2] == 'john@example.com'

    # Test named access (as dict)
    assert row['id'] == 1
    assert row['name'] == 'John Doe'
    assert row['email'] == 'john@example.com'

    # Test slice access (critical for SQL adapter)
    assert row[:] == [1, 'John Doe', 'john@example.com']
    assert row[0:2] == [1, 'John Doe']
    assert row[1:] == ['John Doe', 'john@example.com']

    # Test negative indexing
    assert row[-1] == 'john@example.com'
    assert row[-2] == 'John Doe'

    # Test iteration
    result = list(row)
    assert result == [1, 'John Doe', 'john@example.com']

    # Test len
    assert len(row) == 3


def test_GnrNamedList_sql_adapter_with_duplicates():
    """Test GnrNamedList with duplicate column names (from reader with duplicates)"""
    # Simulate reader that renamed duplicate columns
    index = {'id': 0, 'value': 1, 'value[2]': 2, 'value[3]': 3}
    values = [1, 10, 20, 30]

    row = gl.GnrNamedList(index, values=values)

    # Test all columns are accessible
    assert row['id'] == 1
    assert row['value'] == 10
    assert row['value[2]'] == 20
    assert row['value[3]'] == 30

    # Test numeric access still works
    assert row[0] == 1
    assert row[1] == 10
    assert row[2] == 20
    assert row[3] == 30

    # Test slice access
    assert row[:] == [1, 10, 20, 30]
    assert row[1:] == [10, 20, 30]


def test_GnrNamedList_mixed_access_patterns():
    """Test GnrNamedList with various access patterns used in production code"""
    index = {'transaction_id': 0, 'user_name': 1, 'amount': 2}
    values = ['TX123', 'Alice', 100.50]

    row = gl.GnrNamedList(index, values=values)

    # Common patterns used in tableImporterCheck and related code

    # Pattern 1: Iterate and access by name
    for item in row:
        assert item is not None

    # Pattern 2: Convert to dict
    row_dict = dict(row)
    assert 'transaction_id' in row_dict or 0 in row_dict

    # Pattern 3: Slice and process
    subset = row[1:]
    assert len(subset) == 2
    assert subset[0] == 'Alice'

    # Pattern 4: Check membership (for index)
    assert 'transaction_id' in row._index
    assert 'user_name' in row._index

    # Pattern 5: Enumerate
    for i, value in enumerate(row):
        assert row[i] == value


class TestCsvReader:
    """Test suite for CsvReader class"""

    def test_basics(self):
        test_dir = os.path.dirname(__file__)
        test_file = os.path.join(test_dir, "data", "test.csv")
        a = ff.CsvReader(test_file)
        # FIXME: odd interface using __call__
        r = [x for x in a()]
        assert len(r) == 1
        assert isinstance(r[0], gl.GnrNamedList)
        assert 'a' in r[0].keys()
        a = ff.CsvReader(test_file, detect_encoding=True)


    def test_duplicate_columns(self):
        """Test handling of duplicate column names in CSV files"""
        import tempfile
        import csv

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            csv_file = f.name
            writer = csv.writer(f)
            # Headers with duplicate 'name' column
            writer.writerow(['id', 'name', 'surname', 'name', 'email'])
            writer.writerow(['1', 'Mario', 'Rossi', 'Giuseppe', 'mario@test.com'])
            writer.writerow(['2', 'Laura', 'Bianchi', 'Anna', 'laura@test.com'])

        try:
            reader = ff.CsvReader(csv_file)

            # Check that duplicate column has been renamed
            assert 'name' in reader.headers
            assert 'name[3]' in reader.headers
            assert reader.headers == ['id', 'name', 'surname', 'name[3]', 'email']

            # Check index mapping
            assert reader.index['name'] == 1
            assert reader.index['name[3]'] == 3

            # Read rows
            rows = [row for row in reader()]
            assert len(rows) == 2

            # Test first row
            row = rows[0]
            assert row[0] == '1'
            assert row[1] == 'Mario'
            assert row[2] == 'Rossi'
            assert row[3] == 'Giuseppe'
            assert row[4] == 'mario@test.com'

            # Access by name
            assert row['id'] == '1'
            assert row['name'] == 'Mario'
            assert row['surname'] == 'Rossi'
            assert row['name[3]'] == 'Giuseppe'
            assert row['email'] == 'mario@test.com'

        finally:
            os.unlink(csv_file)


    def test_quoted_decimals(self):
        """Test CsvReader correctly reads quoted decimal values in different formats (EUR vs USA)"""
        test_dir = os.path.dirname(__file__)

        test_cases = [
            ('test_CsvAuto_CommaQuotedDecimalsEUR.csv', '-50,00'),  # European format: comma as decimal separator
            ('test_CsvAuto_CommaQuotedDecimalsUSA.csv', '-50.00'),  # US format: period as decimal separator
        ]

        expected_description = 'PAGAMENTO   CARTA DEBITO;\tINTERNAZIONALE: "5375******3179" -03/01/26-13:49 BIANCHI NEGOZIO ABBIGLIAMENTO -ITA'

        for filename, expected_importo in test_cases:
            test_file = os.path.join(test_dir, 'data', filename)

            # Detect dialect first, then create CsvReader
            dialect = ff.getCsvDialect(test_file, encoding='utf-8')
            reader = ff.CsvReader(test_file, dialect=dialect, encoding='utf-8')

            assert reader.ncols == 11
            assert reader.headers[0] == 'Data contabile'
            assert reader.headers[10] == 'Note'

            rows = list(reader())
            assert len(rows) == 6

            last_row = rows[5]
            assert last_row[2] == expected_importo
            assert last_row[9] == expected_description

    def test_encoding_detection(self):
        """Test CsvReader with detect_encoding=True on files with various encodings.

        Verifies that:
        1. Header is correctly read (slugified to 'id,nome,citta,descrizione' or similar)
        2. Last row, 4th field (descrizione) contains encoding-specific characters
        """
        test_dir = os.path.dirname(__file__)

        # Map filename to expected last row description field
        # Each file has different content in the last row's 'descrizione' field
        test_cases = [
            ('test_Enc_ASCII.csv', ['id', 'nome', 'citta', 'descrizione'], 'Descrizione semplice e pulita'),
            ('test_Enc_UTF8.csv', ['id', 'nome', 'città', 'descrizione'], 'Текст на русском языке'),
            ('test_Enc_ISO8859_1.csv', ['id', 'nome', 'città', 'descrizione'], 'Größe und Qualität'),
            ('test_Enc_Windows1252.csv', ['id', 'nome', 'città', 'descrizione'], 'Größe™ und Qualität'),
            ('test_Enc_Windows1251.csv', ['id', 'name', 'city', 'description'], 'Белорусская столица'),
            ('test_Enc_Windows1253.csv', ['id', 'name', 'city', 'description'], 'Νησί της Κρήτης €'),
            ('test_Enc_KOI8R.csv', ['id', 'name', 'city', 'description'], 'Дальний Восток России'),
            ('test_Enc_SHIFTJIS.csv', ['id', 'name', 'city', 'description'], '北海道の首都'),
            ('test_Enc_EUCKR.csv', ['id', 'name', 'city', 'description'], '영남지방 중심도시'),
            ('test_Enc_GB2312.csv', ['id', 'nome', 'città', 'descrizione'], '经济特区城市'),
        ]

        for filename, expected_header, expected_last_descrizione in test_cases:
            test_file = os.path.join(test_dir, 'data', filename)

            reader = ff.CsvReader(test_file, detect_encoding=True)

            assert reader.headers == expected_header

            rows = list(reader())
            last_row = rows[-1]

            assert last_row[3] == expected_last_descrizione

    def test_start_at_line(self):
        """Test CsvReader start_at_line parameter skips header lines correctly.

        Uses test_CsvAuto_Colon_skipLines.csv which has 12 lines of metadata before the actual CSV data.
        With start_at_line=12, results should be identical to test_CsvAuto_Colon.csv without the parameter.
        """
        test_dir = os.path.dirname(__file__)

        # Reference file (no skip)
        reference_file = os.path.join(test_dir, 'data', 'test_CsvAuto_Colon.csv')
        dialect = ff.getCsvDialect(reference_file, encoding='utf-8')
        reference_reader = ff.CsvReader(reference_file,
                                        dialect=dialect, encoding='utf-8')
        reference_rows = list(reference_reader())

        # File with metadata to skip
        START_LINE = 12
        skip_file = os.path.join(test_dir, 'data', 'test_CsvAuto_Colon_skipLines.csv')
        dialect = ff.getCsvDialect(skip_file, encoding='utf-8',
                                   start_at_line=START_LINE)
        skip_reader = ff.CsvReader(skip_file,
                                   dialect=dialect, encoding='utf-8',
                                   start_at_line=START_LINE)
        skip_rows = list(skip_reader())

        assert reference_reader.headers == skip_reader.headers
        assert len(reference_rows) == len(skip_rows)

        for ref_row, skip_row in zip(reference_rows, skip_rows):
            for j in range(len(ref_row)):
                assert ref_row[j] == skip_row[j]

    def test_auto_dialect(self):
        """Test CsvReader with automatic dialect detection via getCsvDialect.

        Verifies that CsvReader correctly reads CSV files with various delimiters
        (comma, semicolon, tab, pipe, colon) when dialect is detected via getCsvDialect.
        """
        test_dir = os.path.dirname(__file__)

        # Test files with different delimiters and decimal formats
        test_files = [
            ('test_CsvAuto_Colon.csv', '-50,00'),
            ('test_CsvAuto_Comma.csv', '-50.00'),
            ('test_CsvAuto_CommaQuotedDecimalsEUR.csv', '-50,00'),
            ('test_CsvAuto_CommaQuotedDecimalsUSA.csv', '-50.00'),
            ('test_CsvAuto_Pipe.csv', '-50,00'),
            ('test_CsvAuto_SemiColon.csv', '-50,00'),
            ('test_CsvAuto_Tab.csv', '-50,00'),
        ]

        expected_description = 'PAGAMENTO   CARTA DEBITO;\tINTERNAZIONALE: "5375******3179" -03/01/26-13:49 BIANCHI NEGOZIO ABBIGLIAMENTO -ITA'

        for filename, expected_importo in test_files:
            test_file = os.path.join(test_dir, 'data', filename)

            # Detect dialect first, then create CsvReader
            dialect = ff.getCsvDialect(test_file, encoding='utf-8')
            reader = ff.CsvReader(test_file, dialect=dialect, encoding='utf-8')

            assert reader.ncols == 11
            assert reader.headers[0] == 'Data contabile'
            assert reader.headers[10] == 'Note'

            rows = list(reader())
            assert len(rows) == 6

            last_row = rows[5]
            assert last_row[2] == expected_importo
            assert last_row[9] == expected_description
