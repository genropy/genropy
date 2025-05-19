import os
import tempfile

import pytest

import gnr.app.gnrdeploy as gd

from common import BaseGnrAppTest


class TestGnrAppDeployPathResolver(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.pr = gd.PathResolver()
        
    def test_js_path(self):
        r = self.pr.js_path()
        assert r is not None
        assert r.endswith('js')


    def test_entity_name_to_path(self):
        r = self.pr.entity_name_to_path("sys", "package")
        assert "gnrcore/packages/sys" in r

        with pytest.raises(gd.EntityNotFoundException):
            r = self.pr.entity_name_to_path("goober", "package")
        
        with pytest.raises(gd.UnknownEntityTypeException):
            r = self.pr.entity_name_to_path("goober", "skirtsteak")

        os.environ['GNR_LOCAL_PROJECTS'] = "."
        r = self.pr.entity_name_to_path("sys", "package")
        assert "gnrcore/packages/sys" in r

        SITE_NAME = "gnrdevelop"
        r1 = self.pr.entity_name_to_path(SITE_NAME, "site")
        r2 = self.pr.site_name_to_path(SITE_NAME)
        assert r1 == r2
        os.environ.pop('GNR_LOCAL_PROJECTS')

    def test_get_instanceconfig(self):
        r = self.pr.get_instanceconfig("gnrtest")

    def test_get_siteconfig(self):
        r = self.pr.get_siteconfig("gnrtest")
        print(r)
        
