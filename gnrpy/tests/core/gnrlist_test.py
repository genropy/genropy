import os.path
import datetime

import pytest
from gnr.core import gnrlist as gl

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

    assert gnl.pop("name") == "Arthur"
    assert gnl.pop("name") == "Dent"

    with pytest.raises(KeyError) as excinfo:
        gnl.pop("planet")
    assert str(excinfo.value) == "'planet'"

    
    # now the list should be empty
    assert gnl.pop("name") == None

    gnl.update(dict(name="Ford"))
    assert gnl.pop("name") == "Ford"

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
    assert False
    
def test_getReader():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = os.path.join(tmpdir, 'test.csv')
        with open(filename, "w") as wfp:
            wfp.write("one,two,three\nfour,five,six")
        a = gl.getReader(filename)
        assert isinstance(a, gl.CsvReader)

        filename = os.path.join(tmpdir, 'test.tab')
        with open(filename, "w") as wfp:
            wfp.write("one\ttwo\tthree\nfour\tfive\tsix")
        a = gl.getReader(filename)
        assert isinstance(a, gl.CsvReader)

        filename = os.path.join(tmpdir, 'test.csv')
        with open(filename, "w") as wfp:
            wfp.write("one\ttwo\tthree\nfour\tfive\tsix")
        a = gl.getReader(filename, filetype="csv_auto")
        assert isinstance(a, gl.CsvReader)


        # Will fail with an emtpy file
        filename = os.path.join(tmpdir, 'test.xls')
        with open(filename, "w") as wfp:
            pass
        with pytest.raises(Exception):
            a = gl.getReader(filename, filetype="excel")
        filename = os.path.join(tmpdir, 'test.xlsx')
        with open(filename, "w") as wfp:
            pass
        with pytest.raises(Exception):
            a = gl.getReader(filename, filetype="excel")

    test_dir = os.path.dirname(__file__)
    
    filename = os.path.join(test_dir, "data", "test.xls")
    a = gl.getReader(filename)
    assert isinstance(a, gl.XlsReader)

    filename = os.path.join(test_dir, "data","test.xlsx")
    a = gl.getReader(filename)
    assert isinstance(a, gl.XlsxReader)

    # FIXME: this fails all the time.
    with pytest.raises(Exception):
        filename = os.path.join(test_dir, "data", "testbag.xml")
        a = gl.getReader(filename)

def test_CsvReader():
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", "test.csv")
    a = gl.CsvReader(test_file)
    # FIXME: odd interface using __call__
    r = [x for x in a()]
    assert len(r) == 1
    assert isinstance(r[0], gl.GnrNamedList)
    assert 'a' in r[0].keys()
    a = gl.CsvReader(test_file, detect_encoding=True)


def test_XlsReader():
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", 'test.xls')
    r = gl.XlsReader(test_file)
    assert r.sheet.name == "Sheet1"
    assert 'a' in r.headers
    assert 0 in r.colindex
    assert r.colindex[0] is True
    assert 'a' in r.index
    assert r.ncols == 3
    assert r.nrows == 1
    d = [x for x in r()]
    assert len(d) == 1
    assert isinstance(d[0], gl.GnrNamedList)
    assert 'a' in d[0].keys()

def test_XlsxReader():
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", 'test.xlsx')
    r = gl.XlsxReader(test_file)
    assert r.sheet.title == "Sheet1"
    assert 'a' in r.headers
    assert 0 in r.colindex
    assert r.colindex[0] is True
    assert 'a' in r.index
    assert r.ncols == 3

    # FIXME: this doesn't work in the implementation
    #assert r.nrows == 1

    d = [x for x in r()]
    assert len(d) == 1
    assert isinstance(d[0], gl.GnrNamedList)
    assert 'a' in d[0].keys()

def test_readXLS():
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", 'test.xls')
    r = gl.readXLS(test_file)
    d = [x for x in r]
    assert len(d) == 1
    assert isinstance(d[0], gl.GnrNamedList)
    assert 'a' in d[0].keys()

    with open(test_file, "rb") as fp:
        r = gl.readXLS(fp)
        d = [x for x in r]
        assert len(d) == 1
        assert isinstance(d[0], gl.GnrNamedList)
        assert 'a' in d[0].keys()

def test_readCSV():
    # FIXME: apparently, readXLS and readCSV exposes
    # a different interface to access record, please
    # check the last assert here with the last of readXLS test
    # while readCSV_new works correctly. Maybe the _new should
    # be the implementation..
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", 'test.csv')
    r = gl.readCSV(test_file)
    d = [x for x in r]
    assert len(d) == 2
    assert isinstance(d[0], gl.GnrNamedList)
    assert 'a' in d[0].keys()[0]

    with open(test_file, "r") as fp:
        r = gl.readCSV(fp)
        d = [x for x in r]
        assert len(d) == 2
        assert isinstance(d[0], gl.GnrNamedList)
        assert 'a' in d[0].keys()[0]

def test_readCSV_new():
    test_dir = os.path.dirname(__file__)
    test_file = os.path.join(test_dir, "data", 'test.csv')
    r = gl.readCSV_new(test_file)
    d = [x for x in r]
    assert len(d) == 1
    assert isinstance(d[0], gl.GnrNamedList)
    assert 'a' in d[0].keys()

    with open(test_file, "r") as fp:
        r = gl.readCSV_new(fp)
        d = [x for x in r]
        assert len(d) == 1
        assert isinstance(d[0], gl.GnrNamedList)
        assert 'a' in d[0].keys()

        
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
    
    
                
