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

    def _error_rows(self, pkey):
        db = self.site.db
        db.closeConnection()
        return db.table('sys.error').query(
            columns='$description,$error_type,$error_code', where='$id=:pkey',
            pkey=pkey).fetch()

    def _drop_error_row(self, pkey):
        db = self.site.db
        db.table('sys.error').deleteSelection(where='$id=:pkey', pkey=pkey)
        db.commit()

    def test_deprecated_write_exception_returns_the_record(self):
        flow_completed = False
        try:
            raise ValueError('legacy site failure')
        except ValueError as e:
            with pytest.warns(DeprecationWarning, match='writeException'):
                rec = self.site.writeException(exception=e)
            flow_completed = True
        assert flow_completed
        assert rec and rec['id']
        try:
            assert rec['error_code']
            assert rec['error_type'] == 'EXC'
            assert rec['description'] == 'legacy site failure'
            rows = self._error_rows(rec['id'])
            assert len(rows) == 1
            assert rows[0]['error_code'] == rec['error_code']
        finally:
            self._drop_error_row(rec['id'])

    def test_deprecated_write_exception_keeps_supplied_traceback(self):
        supplied_traceback = 'traceback captured before reporting'
        with pytest.warns(DeprecationWarning, match='writeException'):
            rec = self.site.writeException(
                exception=ValueError('legacy site failure'),
                traceback=supplied_traceback)
        assert rec and rec['id']
        try:
            self.site.db.closeConnection()
            stored = self.site.db.table('sys.error').record(pkey=rec['id']).output('dict')
            assert stored['error_data'] == supplied_traceback
        finally:
            self._drop_error_row(rec['id'])

    def test_deprecated_write_error_returns_the_record(self):
        assert not getattr(self.site.writeError, 'is_rpc', False)
        with pytest.warns(DeprecationWarning, match='writeError'):
            rec = self.site.writeError(description='legacy site error')
        assert rec and rec['id']
        try:
            assert rec['error_type'] == 'ERR'
            rows = self._error_rows(rec['id'])
            assert len(rows) == 1
            assert rows[0]['description'] == 'legacy site error'
        finally:
            self._drop_error_row(rec['id'])

    def test_deprecated_write_error_keeps_kwargs_in_error_data(self):
        with pytest.warns(DeprecationWarning, match='writeError'):
            rec = self.site.writeError(description='legacy kwargs', extra_info='KWVAL',
                                       loglevel='warning', error_id='legacy_id')
        assert rec and rec['id']
        try:
            self.site.db.closeConnection()
            stored = self.site.db.table('sys.error').record(pkey=rec['id']).output('dict')
            error_data = str(stored['error_data'])
            assert 'KWVAL' in error_data
            assert 'legacy_id' in error_data
            assert stored['error_code'] != 'legacy_id'
        finally:
            self._drop_error_row(rec['id'])

    def test_deprecated_write_error_never_raises(self, monkeypatch):
        def failing_error_handler(**kwargs):
            raise RuntimeError('error handler failure')
        monkeypatch.setattr(self.site, 'errorHandler', failing_error_handler)
        with pytest.warns(DeprecationWarning):
            rec = self.site.writeError(description='failing write')
        assert rec is None

    def _rpc_write_error(self, page, description):
        previous_page = self.site.currentPage
        self.site.currentPage = page
        try:
            handler = page.getPublicMethod('rpc', 'site.writeError')
            result = handler(description=description, extra_info='KWVAL')
        finally:
            self.site.currentPage = previous_page
        db = self.site.db
        db.closeConnection()
        rows = db.table('sys.error').query(
            columns='$id', where='$description=:d', d=description).fetch()
        for row in rows:
            self._drop_error_row(row['id'])
        return result, len(rows)

    def test_rpc_write_error_refuses_a_page_without_user(self):
        result, written = self._rpc_write_error(self.site.dummyPage, 'rpc no user')
        assert result is None
        assert written == 0

    def test_rpc_write_error_refuses_a_guest(self):
        page = self.site.dummyPage
        page.user = page.connection.guestname
        assert page.isGuest
        result, written = self._rpc_write_error(page, 'rpc guest')
        assert result is None
        assert written == 0

    def test_rpc_write_error_writes_for_a_logged_user_and_returns_nothing(self):
        page = self.site.dummyPage
        page.avatar = self.site.gnrapp.makeAvatar(user='rpc_tester', user_id='rpc_tester')
        result, written = self._rpc_write_error(page, 'rpc logged user')
        assert result is None
        assert written == 1
