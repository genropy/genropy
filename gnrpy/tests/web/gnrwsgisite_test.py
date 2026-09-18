import os
import pytest

import gnr.web.gnrwsgisite as gws

from webcommon import BaseGnrDaemonTest


class TestGnrWsgiSite(BaseGnrDaemonTest):
    def test_site_structure(self):
        assert gws.GNRSITE == self.site
        assert "gnrcore" in self.site.site_path
        assert "gnrdevelop" in self.site.site_path
        assert self.site.project_name is None
        assert self.site.home_uri == '/'
        assert self.site.remote_edit is None
        assert self.site.locale
        
    def test_root_domain_home_uri(self, monkeypatch):
        assert not self.site.multidomain
        assert self.site.rootDomainHomeUri == self.site.default_uri
        monkeypatch.setattr(type(self.site.db), 'multidb_config',
                            property(lambda db: {'multidomain': 'true'}))
        assert self.site.multidomain
        assert self.site.rootDomainHomeUri == f'{self.site.default_uri}{self.site.rootDomain}/'
        assert self.site.rootDomainHomeUri == '/_main_/'

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

    def test_missing_page_returns_404(self):
        # issue #890: unresolvable urls fall back to sys/default,
        # which must answer 404, not 200
        response = self.client.get('/antani/come/se/fosse')
        assert "404 " in response.get('status')
        # and the 404 body must be lightweight: no framework envelope,
        # no client bootstrap (that costs megabytes of js/css per hit)
        body = response.get('data')
        assert b'dojo' not in body
        assert b'genro' not in body
        assert len(body) < 1024

    def test_directory_index_still_serves(self):
        # a url that maps to a webpages folder without index.py is a
        # legitimate use of the sys/default catch-all: it must keep
        # answering 200 with the full framework page (directory browser)
        response = self.client.get('/sys/test')
        assert "200 " in response.get('status')
        assert b'genro' in response.get('data')
        


