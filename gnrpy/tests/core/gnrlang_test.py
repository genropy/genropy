import pytest
import os
import threading
from gnr.core import gnrlang as gl
from gnr.core.gnrbag import Bag
from gnr.core.gnrerror import tracebackBag

class TestGnrLang():
    def test_getUuid(self):
        r1 = gl.getUuid()
        assert len(r1) == 22
        r2= gl.getUuid()
        assert len(r2) == 22
        assert r1 != r2

    def test_get_caller_info(self):

        def t1():
            return gl.get_caller_info()

        r = t1()
        for x in ['line_number', 'function_name',
                  'module_name']:
            assert x in r
        assert r['function_name'] == 'test_get_caller_info'
        assert 'gnrlang_test' in r['module_name']
        
        
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
        assert r == 0
        r = gl.position("x", "hello")
        assert r == -1
        r = gl.position("hi", ["hello", "hi", "aye"])
        assert r == 1

        with pytest.raises(AttributeError):
            r = gl.position("g", gl.position)

    def test_uniquify(self):
        r = gl.uniquify("hello")
        assert r.count('l') == 1

    def test_args(self):
        r = gl.args(1,2,3,a=1,b=2,c=3)
        assert r[0] == (1,2,3)
        assert r[1].get('a', None) == 1
        assert r[1].get('b', None) == 2
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
        assert gl.boolean("T") == True
        assert gl.boolean("F") == False
        assert gl.boolean("t") == True
        assert gl.boolean("f") == False
        assert gl.boolean("Y") == True
        assert gl.boolean("N") == False
        assert gl.boolean(True) == True
        assert gl.boolean(False) == False
        assert gl.boolean([1]) == True
        assert gl.boolean([]) == False

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
        assert e.topic == 1

    def test_BaseProxy(self):
        e = gl.BaseProxy(1)
        assert e.main == 1

    def test_tracebackBag(self):
        r = tracebackBag()
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


class TestClassMixinProxy():
    def test_legacy_true_uses_lowercase_class_name(self):
        class Target(object):
            pass

        class Proxy_test(object):
            proxy = True

            def ping(self):
                return 'pong'

        gl.classMixin(Target, Proxy_test)

        assert hasattr(Target, 'proxy_test_proxyclass')
        assert Target.proxy_test_proxyclass.ping.proxy_name == 'proxy_test'

    def test_legacy_named_proxy_composes_components(self):
        class Target(object):
            pass

        class FirstComponent(object):
            proxy = 'shared'

            def first(self):
                return 'first'

        class SecondComponent(object):
            proxy = 'shared'

            def second(self):
                return 'second'

        gl.classMixin(Target, FirstComponent)
        gl.classMixin(Target, SecondComponent)

        page = Target()
        page.shared = Target.shared_proxyclass(page)
        assert page.shared.first() == 'first'
        assert page.shared.second() == 'second'

    def test_proxy_name_precedes_legacy_proxy(self):
        class Target(object):
            pass

        class Component(object):
            proxy = 'legacy'
            proxy_name = 'modern'

            def ping(self):
                return 'pong'

        gl.classMixin(Target, Component)

        assert hasattr(Target, 'modern_proxyclass')
        assert not hasattr(Target, 'legacy_proxyclass')
        assert Target.modern_proxyclass.ping.proxy_name == 'modern'

    def test_proxy_instantiation_preserves_serialized_rpc_name(self):
        class Target(object):
            pass

        class Component(object):
            proxy = 'shared'

            def rpc_ping(self):
                return 'pong'

        gl.classMixin(Target, Component)

        page = Target()
        page.shared = Target.shared_proxyclass(page)
        assert page.shared.main is page
        assert page.shared.rpc_ping() == 'pong'
        assert gl.serializedFuncName(page.shared.rpc_ping) == 'shared.ping'


class TestGnrLang_getEncoding():
    def _get_data_path(self, filename):
        return os.path.join(os.path.dirname(__file__), 'data', filename)

    def test_getEncoding_ascii(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_ASCII.csv'))
        assert result.lower() == 'ascii'

    def test_getEncoding_utf8(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_UTF8.csv'))
        assert result.lower() == 'utf-8'

    def test_getEncoding_iso8859_1(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_ISO8859_1.csv'))
        assert result.lower() == 'iso-8859-1'

    def test_getEncoding_windows1251(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_Windows1251.csv'))
        assert result.lower() == 'windows-1251'

    def test_getEncoding_windows1252(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_Windows1252.csv'))
        assert result.lower() == 'windows-1252'

    def test_getEncoding_windows1253(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_Windows1253.csv'))
        assert result.lower() == 'windows-1253'

    def test_getEncoding_gb2312(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_GB2312.csv'))
        assert result.lower() == 'gb2312'

    def test_getEncoding_euckr(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_EUCKR.csv'))
        assert result.lower() == 'euc-kr'

    def test_getEncoding_koi8r(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_KOI8R.csv'))
        assert result.lower() == 'koi8-r'

    def test_getEncoding_shiftjis(self):
        result = gl.getEncoding(self._get_data_path('test_Enc_SHIFTJIS.csv'))
        assert result.lower() == 'shift_jis'

    def test_getEncoding_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            gl.getEncoding(self._get_data_path('nonexistent_file.csv'))


def test_gnrImport_path_cache(tmp_path):
    source = tmp_path / 'dummy_cached_module.py'
    source.write_text('class Service(object):\n    pass\n')
    first = gl.gnrImport(str(source), avoidDup=True)
    second = gl.gnrImport(str(source), avoidDup=True)
    assert first is second


def test_gnrImport_avoid_module_cache_returns_fresh_module(tmp_path):
    source = tmp_path / 'dummy_reloaded_module.py'
    source.write_text('VERSION = 1\n')
    first = gl.gnrImport(str(source), avoidDup=True)
    assert first.VERSION == 1
    # different size on purpose: a same-size same-mtime rewrite would be
    # served from the stale bytecode cache by the source loader
    source.write_text('VERSION = 2000\n')
    reloaded = gl.gnrImport(str(source), avoidDup=True, avoid_module_cache=True)
    assert reloaded.VERSION == 2000
    cached = gl.gnrImport(str(source), avoidDup=True)
    assert cached is reloaded


def test_gnrImport_concurrent_single_module_identity(tmp_path):
    source = tmp_path / 'dummy_concurrent_module.py'
    source.write_text('class Service(object):\n    pass\n')
    modules = []

    def worker():
        modules.append(gl.gnrImport(str(source), avoidDup=True))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(modules) == 8
    assert all(m is modules[0] for m in modules)
    assert modules[0].Service is not None


# ---------------------------------------------------------------------------
# ThreadedDict
# ---------------------------------------------------------------------------


def test_threaded_dict_get_default_is_none():
    td = gl.ThreadedDict()
    assert td.get() is None


def test_threaded_dict_set_then_get_roundtrip():
    td = gl.ThreadedDict()
    td.set('value')
    assert td.get() == 'value'


def test_threaded_dict_set_none_pops_entry():
    """Assigning None removes the current thread's entry instead of
    storing it, so the backing dict does not keep a live-but-empty slot
    for every thread that ever called set()."""
    td = gl.ThreadedDict()
    td.set('value')
    assert len(td._data) == 1
    td.set(None)
    assert td.get() is None
    assert len(td._data) == 0


def test_threaded_dict_isolated_across_threads():
    """Each thread sees only the value it set, keyed by its own ident.

    A thread that exits without explicitly resetting to None leaves its
    entry behind: ThreadedDict itself does no bookkeeping on thread exit,
    so callers (e.g. GnrWsgiSite.cleanup()) are responsible for popping
    their slot with set(None) before the thread ends. Skipping that step
    is exactly the unbounded per-thread growth fixed by #379/#380.
    """
    td = gl.ThreadedDict()
    results = {}

    def worker(name):
        td.set(name)
        results[name] = td.get()
        td.set(None)  # mirrors the app's own cleanup-on-exit responsibility

    threads = [threading.Thread(target=worker, args=(name,))
               for name in ('thread_a', 'thread_b', 'thread_c')]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == {'thread_a': 'thread_a',
                        'thread_b': 'thread_b',
                        'thread_c': 'thread_c'}
    # each worker popped its own entry before exiting: nothing left behind
    assert len(td._data) == 0
