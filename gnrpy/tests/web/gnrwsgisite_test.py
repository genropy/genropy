import os
import time
import pytest

import gnr.web.gnrwsgisite as gws

from webcommon import BaseGnrTest
from utils import WSGITestClient, ExternalProcess

def get_waited_wsgisite(site_name):
    max_attempts = 3
    attempt = 0
    timeout = 2
    
    while attempt < max_attempts:
        try:
            site = gws.GnrWsgiSite(site_name, site_name=site_name)
            return site
        except Exception as e:
            time.sleep(timeout)
            attempt += 1
    raise Exception(f"Can't connect to local daemon after {attempt} attempts")

class TestGnrWsgiSite(BaseGnrTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        
        cls.external = ExternalProcess(
            ['gnr','web','daemon', '-P', str(cls.daemon_port)],
            port_check = cls.daemon_port, cwd=None
        )

        try:
            cls.external.start()
            cls.site_name = 'gnrdevelop'
            cls.site = get_waited_wsgisite(cls.site_name)
            cls.client = WSGITestClient(cls.site)
            cls.services_handler = cls.site.services_handler
        except Exception as e:
            # re-raise to take care of the problem, but ensuring the external
            # process is being terminated.
            cls.teardown_class()
            raise
        
    @classmethod
    def teardown_class(cls):
        cls.external.stop()
        super().teardown_class()

    def test_site_structure(self):
        assert gws.GNRSITE == self.site
        assert "gnrcore" in self.site.site_path
        assert "gnrdevelop" in self.site.site_path
        assert self.site.project_name is None
        assert self.site.home_uri == '/'
        assert self.site.remote_edit is None
        assert self.site.locale
        
    def test_apikeys(self):
        r = self.site.getApiKeys("booger")
        assert r is None
        r = self.site.getApiKeys("foobar")
        assert "value" in r
        assert "hellothere" in r.values()
        
    def test_storage_path(self):

        # Test with single storage type
        storages = ['boogerbin']
        storage_path = 'misc'
        for storage in storages:
            r = self.site.storagePath(storage, storage_path)
            assert r.endswith(storage_path)
 
    def test_service_handler(self):
        # non existing service
        with pytest.raises(KeyError) as excinfo:
            r = self.services_handler("foobar").configurations()
            
        r = self.site.getService("foobar", "goober")
        assert r is None
        r = self.site.getService("git", "gitpython")
        assert r is None
        assert "git" in self.services_handler.service_types

    def test_auxinstances(self):
        with pytest.raises(Exception) as excinfo:
            r = self.site.getAuxInstance("babbala")

    def test_site_config(self):
        r = self.site.siteConfigPath()
        assert os.path.exists(r)

    def test_path_list(self):
        path1 = self.site.get_path_list('/')
        assert len(path1) == 1
        assert path1[0] == 'index'
        path2 = self.site.get_path_list('')
        assert len(path2) == 1
        assert path2[0] == 'index'

        path3 = self.site.get_path_list('..//..//./')
        assert len(path3) == 3
        assert '/' not in path3
        assert path3[0] == '..'

        path4 = self.site.get_path_list('..//..//../etc/passwd')
        assert len(path4) == 5
        assert '/' not in path4
        assert path4[0] == '..'

    def test_urlinfo_routing(self):
        r = self.client.get("/webpages/")
        r = self.client.get("/sys/_plugin/")
        
    def test_guest_counter(self):
        assert self.site.guest_counter == 1

    def test_basic_requests(self):
        response = self.client.get('/')
        assert "200 " in response.get('status')
        response = self.client.get('/_resources/')
        assert "404 " in response.get('status')
        response = self.client.get('/sys/')
        assert "200 " in response.get('status')
        


