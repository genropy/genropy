import sys
import os.path
import pytest
import gnr.app.gnrapp as ga
from common import BaseGnrTest
import sys
    
class TestGnrApp(BaseGnrTest):
    app_name = 'gnrdevelop'
    app = ga.GnrApp(app_name, forTesting=True)

    def test_nullloader(self):
        a = ga.NullLoader()
        r = a.load_module('sys')
        assert r == sys
        r = a.load_module('babbala')
        assert r == None
    
    def test_ApplicationCache(self):
        ac = ga.ApplicationCache()
        assert ac.application is None
        assert len(ac.cache.items()) == 0
        
        ac = ga.ApplicationCache(self.app)
        assert ac.application.instanceName == self.app_name
        
        ac.setItem(1, "one")
        assert len(ac.cache.items()) == 1
        
        r = ac.getItem(1)
        assert r == "one"
        
        assert ac.expiredItem(1) == False
        
        ac.updatedItem(1)
        assert len(ac.cache.items()) == 0
        
        assert ac.expiredItem(1) == True

    def test_GnrModuleFinder(self):
        with pytest.raises(ImportError) as excinfo:
            mf = ga.GnrModuleFinder("/", self.app)
        assert excinfo.typename == "ImportError"
        path_test = os.path.join(self.app.instanceFolder, "lib")

        mf = self.app.get_modulefinder(path_test)
        
        mf_str = str(mf)

        assert mf_str == f'<GnrModuleFinder for "{path_test}">'

        r = mf.pkg_in_app_list("babbala")
        assert r == None

        r = mf.pkg_in_app_list("sys")
        assert r.id == 'sys'

        r = mf.find_module("gnrpkg")
        assert type(r) == type(ga.NullLoader())

        # FIXME - can't find a valid entry for >2 component path 
        with pytest.raises(ImportError) as excinfo:
            r = mf.find_module('gnrpkg.sys.menu')

        r = mf.find_module('gnrpkg.gnrcore.sys')
        assert r is None

        r = mf.find_module('gnrpkg.sys')
        assert type(r) == type(ga.NullLoader())

    def test_GnrModuleLoader(self):
        ml = ga.GnrModuleLoader("sys", self.test_app_path, "Sysadmin modules")
        mod = ml.load_module("gnrpkg.sys")
        assert 'gnrpkg.sys' in sys.modules

        # FIXME: waiting for IMP vs Importlib changes
        with pytest.raises(AttributeError) as excinfo:
            mod = ml.load_module("gnrpkg.adm")

    def test_GnrPackagePlugin(self):
        r = self.app.packages['sys'].loadPlugins()
        assert r is None
        
    def test_GnrMixinObj(self):
        mo = ga.GnrMixinObj()

    def test_GnrAvatar(self):
        a = ga.GnrAvatar("adm", testing="goober")
        assert a.user == "adm"

        a.addTags("goober,foobar")
        assert "goober" in a.user_tags
        a.addTags("goober")
        assert a.user_tags.split(',').count("goober") == 1

        at = getattr(a, "testing")
        assert at == "goober"

        at = a.testing
        assert at == "goober"

        with pytest.raises(AttributeError) as excinfo:
            at = getattr(a, "testing2")
            at = a.testing2

        ad = a.as_dict()
        assert a.user_name is None
        assert "user" in ad
        assert "testing" in ad

    def test_hostedBy(self):
        r = self.app.hostedBy
        assert r is None

    def test_gnrdaemon(self):
        d = self.app.gnrdaemon
        assert d 
