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
