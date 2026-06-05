import os

import pytest

import gnr.app.pathresolver as pr

from common import BaseGnrAppTest


class TestGnrAppDeployPathResolver(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.resolver = pr.PathResolver()
        
    def test_js_path(self):
        r = self.resolver.js_path()
        assert r is not None
        assert r.endswith('js')


    def test_entity_name_to_path(self):
        r = self.resolver.entity_name_to_path("sys", "package")
        assert "gnrcore/packages/sys" in r

        with pytest.raises(pr.EntityNotFoundException):
            r = self.resolver.entity_name_to_path("goober", "package")
        
        with pytest.raises(pr.UnknownEntityTypeException):
            r = self.resolver.entity_name_to_path("goober", "skirtsteak")

        os.environ['GNR_LOCAL_PROJECTS'] = "."
        r = self.resolver.entity_name_to_path("sys", "package")
        assert "gnrcore/packages/sys" in r

        SITE_NAME = "gnrdevelop"
        r1 = self.resolver.entity_name_to_path(SITE_NAME, "site")
        r2 = self.resolver.site_name_to_path(SITE_NAME)
        assert r1 == r2
        os.environ.pop('GNR_LOCAL_PROJECTS')

    def test_get_instanceconfig(self):
        r = self.resolver.get_instanceconfig("gnrtest")

    def test_get_siteconfig(self):
        r = self.resolver.get_siteconfig("gnrtest")
        print(r)
        
