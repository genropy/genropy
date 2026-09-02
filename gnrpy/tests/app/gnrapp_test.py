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

        # ensure that a GnrSqlAppDb without
        # an application raises a TypeError
        with pytest.raises(TypeError):
            a = ga.GnrSqlAppDb()


    def test_data_retention(self):
        """
        Test app higher level data retention
        method and configurations
        """
        
        default_policy = self.app.defaultRetentionPolicy
        custom_policy = self.app.retentionPolicy

        for p in (default_policy, custom_policy):
            assert isinstance(p, dict)
        
            assert "sys.error" in p
            assert "sys.task_execution" in p
            assert isinstance(p['sys.error']['retention_period'], int)
            assert p['sys.error']['retention_period_default'] == 60
            assert p['sys.error']['filter_column'] == '__ins_ts'
            assert p['sys.error']['retention_period'] == p['sys.error']['retention_period_default']
            assert "extra_where_filter" in p['sys.error']
            assert "extra_where_filter" in p['sys.task_execution']
            assert p['sys.error']['extra_where_filter'] == None
            assert p['sys.task_execution']['extra_where_filter'] == None
       


class TestUserTagsOrder(object):
    """The user tags string must not depend on set iteration order (#1173).

    Python randomises string hashing at every process start, so joining a set
    gave a different order in every process. The value travels into the
    connection register item, the avatar and the logs, where an order that
    moves on its own makes two runs impossible to compare.
    """

    def _app(self):
        """makeAvatar with authenticate=False touches nothing else on the app."""
        return object.__new__(ga.GnrApp)

    def test_make_avatar_sorts_the_default_tags(self):
        avatar = self._app().makeAvatar('u', defaultTags='superadmin,_DEV_,admin')
        assert avatar.user_tags == '_DEV_,admin,superadmin'

    def test_make_avatar_sorts_across_both_sources(self):
        """defaultTags and tags are merged, and the merge must sort too."""
        avatar = self._app().makeAvatar('u', defaultTags='user,_SYSTEM_',
                                        tags='level/green,_TRD_')
        assert avatar.user_tags == '_SYSTEM_,_TRD_,level/green,user'

    def test_make_avatar_drops_duplicates_and_blanks(self):
        avatar = self._app().makeAvatar('u', defaultTags='admin,,user',
                                        tags='user,admin')
        assert avatar.user_tags == 'admin,user'

    def test_make_avatar_without_default_tags_is_untouched(self):
        """No defaultTags means the branch never runs: the string passes through."""
        avatar = self._app().makeAvatar('u', tags='b,a')
        assert avatar.user_tags == 'b,a'
