import pytest
from gnr.core import gnrlang as gl
from gnr.core.gnrbag import Bag

class TestGnrLang():
    def test_getUuid(self):
        r1 = gl.getUuid()
        assert len(r1) == 22
        r2= gl.getUuid()
        assert len(r2) == 22
        assert r1 != r2

    def test_mintype_value(self):
        a = gl.MinType()
        assert (a <= -1) is True

        assert a == a
        assert (a == -1) is False

    def test_safedict(self):
        test_dict = {
            1: "ciao",
            "ciao": 1,
            object: []
            }
        sd = gl.safe_dict(test_dict)
        assert '1' in sd
        assert 'ciao' in sd
        assert 1 not in sd
        assert object not in sd

    def test_position(self):
        r = gl.position("h", "hello")
        assert r is 0
        r = gl.position("x", "hello")
        assert r is -1
        r = gl.position("hi", ["hello", "hi", "aye"])
        assert r is 1

        with pytest.raises(AttributeError):
            r = gl.position("g", gl.position)

    def test_uniquify(self):
        r = gl.uniquify("hello")
        assert r.count('l') == 1

    def test_args(self):
        r = gl.args(1,2,3,a=1,b=2,c=3)
        assert r[0] == (1,2,3)
        assert r[1].get('a', None) is 1
        assert r[1].get('b', None) is 2
        assert 'd' not in r[1]
        
    def test_optArgs(self):
        r = gl.optArgs(a=1,b=2,c=None)
        assert 'c' not in r
        assert 'a' in r
        assert r.get('a') == 1
        assert 'b' in r
        assert r.get('b') == 2

    def test_moduleDict(self):
        r = gl.moduleDict('gnr.core.gnrbag', 'Bag,')
        assert not r
        
    def test_boolean(self):
        assert gl.boolean("T") is True
        assert gl.boolean("F") is False
        assert gl.boolean("t") is True
        assert gl.boolean("f") is False
        assert gl.boolean("Y") is True
        assert gl.boolean("N") is False
        assert gl.boolean(True) is True
        assert gl.boolean(False) is False
        assert gl.boolean([1]) is True
        assert gl.boolean([]) is False

    def test_getmixincount(self):
        a = gl.getmixincount()
        assert int(a) == 1

    def test_GnrException(self):
        e = gl.GnrException()
        assert "gnrlang_test.py" in e.description
        e = gl.GnrException(description="Goober")
        assert e.description == "Goober"
        assert e.localizer is None


        class FakeLocalizer(object):
            def translate(self, v):
                return v.replace("goober", "foobar")
            
        localizer = FakeLocalizer()
        # FIXME: this should be fixed in implementation
        e = gl.GnrException(localizer=localizer)
        assert e.localizer is None
        
        e.setLocalizer(localizer)
        assert e.localizer is localizer
        assert e.localize("goober") == "foobar"

        r = e.localizedMsg("goober %(a)s", dict(a="!!Hello"))
        assert r == "foobar !!Hello"

    def test_GnrSilentException(self):
        e = gl.GnrSilentException(topic=1)
        assert e.topic is 1

    def test_BaseProxy(self):
        e = gl.BaseProxy(1)
        assert e.main is 1

    def test_tracebackBag(self):
        r = gl.tracebackBag()
        #FIXME: how to test this properly?

    def test_thlocal(self):
        r = gl.thlocal()
        assert not r

    def test_objectExtract(self):
        class FakeObject(object):
            foobar = 1
            foofight = 2
            goober = 3

        fo = FakeObject()
        r = gl.objectExtract(fo, "foo")
        assert "bar" in r
        assert r['bar'] == 1
        assert 'goober' not in r
        r = gl.objectExtract(fo, "foo", slicePrefix=False)
        assert 'foobar' in r
        assert 'bar' not in r
        assert 'goober' not in r

    def test_importModule(self):
        import sys
        r = gl.importModule('os')
        assert 'os' in sys.modules
        test_module = 'gnr.core.gnrbag'
        r = gl.importModule(test_module)
        assert test_module in sys.modules
        assert r in sys.modules.values()
        with pytest.raises(ModuleNotFoundError):
            r = gl.importModule('goober')

    def test_moduleClasses(self):
        r = gl.moduleClasses(gl.importModule('gnr.core.gnrbag'))
        assert 'Bag' in r

    def test_instanceOf(self):
        r = gl.instanceOf(1)
        assert r == 1

        r = gl.instanceOf('gnr.core.gnrbag:Bag')
        assert isinstance(r, Bag)

        r = gl.instanceOf(Bag)
        print(r)
        assert isinstance(r, Bag)
        
    def test_FilterList(self):
        fl = gl.FilterList()
        fl.extend(["a", "b", "c*"])
        assert "a" in fl
        assert "c" in fl
        # FIXME: the implementation won't allow
        # filtering a list with elements that are
        # not str objects
        with pytest.raises(AttributeError):
            assert 1000 in fl
        assert "d" not in fl
