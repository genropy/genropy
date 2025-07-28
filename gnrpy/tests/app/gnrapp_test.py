"""
Tests for gnr.app package
"""
import sys
import _frozen_importlib
import pytest

from common import BaseGnrAppTest
import gnr.app.gnrapp as ga

class TestGnrApp(BaseGnrAppTest):
    """
    Tests class for gnr.app.gnrapp package
    """
    def setup_method(self, method):
        self.app_name = 'gnrdevelop'
        self.app = ga.GnrApp(self.app_name, forTesting=True)

    def test_nullloader(self):
        """
        Tests for NullLoader
        """
        a = ga.NullLoader('gnrpkg', '.', 'gnrpkg')
        r = a.load_module('sys')
        assert r == sys
        r = a.load_module('babbala')
        assert r is None

    def test_applicationcache(self):
        """
        Tests ApplicationCache
        """
        ac = ga.ApplicationCache()
        assert ac.application is None
        assert len(ac.cache.items()) == 0

        ac = ga.ApplicationCache(self.app)
        assert ac.application.instanceName == self.app_name

        ac.setItem(1, "one")
        assert len(ac.cache.items()) == 1

        r = ac.getItem(1)
        assert r == "one"

        assert ac.expiredItem(1) is False

        ac.updatedItem(1)
        assert len(ac.cache.items()) == 0

        assert ac.expiredItem(1) is True

    def test_gnrmodulefinder(self):
        """
        Tests for GnrModuleFinder
        """


        mf = self.app.get_modulefinder()

        mf_str = str(mf)

        assert mf_str == '<GnrModuleFinder>'

        r = mf.pkg_in_app_list("babbala")
        assert r is None

        r = mf.pkg_in_app_list("sys")
        assert r.id == 'sys'

        r = mf.find_spec("gnrpkg", self.app.instanceFolder)
        assert isinstance(r, _frozen_importlib.ModuleSpec)

        r = mf.find_spec('gnrpkg.gnrcore.sys', self.app.instanceFolder)
        assert r is None

        r = mf.find_spec('gnrpkg.sys', self.app.instanceFolder)
        assert isinstance(r, _frozen_importlib.ModuleSpec)

    def test_gnrpackageplugin(self):
        """
        Tests for GnrPackagePlugin
        """
        r = self.app.packages['sys'].loadPlugins()
        assert r is None

        gpp = ga.GnrPackagePlugin(self.app.packages['sys'], "/")
        assert gpp.path == "/"
        assert gpp.application == self.app

    def test_gnrpackage(self):
        """
        Test for GnrPackage
        """
        p = self.app.packages['sys']
        assert isinstance(p, ga.GnrPackage)
        cfg_attr = p.config_attributes()
        assert cfg_attr['comment'] == 'sys'
        assert cfg_attr['_syspackage']
        assert p.onAuthentication("babbala") is None
        p.configure()

        with pytest.raises(ga.GnrImportException):
            p = ga.GnrPackage("ahhdkjhfjsh", self.app, path=self.test_app_path)
        # TODO: projectInfo attributes for GnrPackage
        # TODO: custom_mixin for GnrPackage
                                
    def test_gnrmixinobj(self):
        """
        Tests for GnrMixinObj"""
        ga.GnrMixinObj()

    def test_gnravatar(self):
        """
        Tests for GnrAvatar
        """
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

        with pytest.raises(AttributeError):
            at = getattr(a, "testing2")
            at = a.testing2

        ad = a.as_dict()
        assert a.user_name is None
        assert "user" in ad
        assert "testing" in ad

    def test_hostedby(self):
        """
        Test hostedBy
        """
        r = self.app.hostedBy
        assert r is None

    def test_gnrdaemon(self):
        """
        Test GnrDaemon app attributes
        """
        d = self.app.gnrdaemon
        assert d

    
    def test_gnrsqlappdb(self):
        """
        Test GnrSqlAppDb class

        FIXME: maybe this should be moved to gnr.sql
        """
        a = ga.GnrSqlAppDb()
        assert a.application is None
