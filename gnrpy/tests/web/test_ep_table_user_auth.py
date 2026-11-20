"""ep_table serves a document to the logged-in user, not to the page id in the url (#1787).

The url of a document (``/sys/ep_table/<pkg>/<tbl>/<pkey>/get/<source>``) carries
the ``_current_page_id`` of the page that built it. The permission used to be
read from that page: the url died with the page, and while the page lived the
page id let anyone download the file. Now the request is authorised by the user
of its own connection (the session cookie), and the page id only tells which
page to refresh.

Every request goes through the real ``sys/ep_table`` page, built by the site's
resource loader from the worktree, on the ``adm.htmltemplate_atc`` attachment
table of the ``gnrtest`` instance and a real file in the ``home`` storage. The
site register is a real in-process ``SiteRegister``: only the Pyro transport to
the daemon is left out.
"""
import uuid

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.daemon.siteregister import SiteRegister
from gnr.web.daemon.siteregister_client import SiteRegisterClient
from gnr.web.gnrcookie import MarshalCookie
from gnr.web.gnrdummysite import GnrDummySite

CONTENT = 'served document'


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


class InProcessRegisterClient(SiteRegisterClient):
    """The site register client, talking to a SiteRegister in this process."""

    def __init__(self, siteregister):
        self.siteregister = siteregister

    def add_data_to_register_item(self, register_item):
        register = self.siteregister.get_register(register_item['register_name'])
        register_item['data'] = register.get_item_data(register_item['register_item_id'])
        return register_item


class TestEpTableUserAuth(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        siteregister = SiteRegister(_FakeServer(), sitename='testsite')
        cls.site._register = InProcessRegisterClient(siteregister)
        cls.db = cls.site.db
        cls.node = cls.site.storageNode(f'home:ep_table_test/{uuid.uuid4().hex}.txt')
        with cls.node.open(mode='w') as f:
            f.write(CONTENT)
        template_id = cls.db.table('adm.htmltemplate').insert(dict(name='ep_table'))['id']
        tbl = cls.db.table('adm.htmltemplate_atc')
        cls.pkey = tbl.insert(dict(maintable_id=template_id, filepath=cls.node.fullpath,
                                   description='ep_table'))['id']
        cls.missing_pkey = tbl.insert(dict(maintable_id=template_id,
                                           filepath='home:ep_table_test/missing.txt',
                                           description='ep_table missing'))['id']
        users = cls.db.table('adm.user')
        user_ids = {}
        for username in ('ep_alice', 'ep_bob', 'ep_carol'):
            user = users.insert(dict(username=username, md5pwd='secret', status='conf',
                                     email=f'{username}@test.local'))
            user_ids[username] = user['id']
        tag_id = cls.db.table('adm.htag').insert(dict(code='ep_reader', description='Reader'))['id']
        cls.db.table('adm.user_tag').insert(dict(user_id=user_ids['ep_carol'], tag_id=tag_id))
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        cls.node.delete()
        super().teardown_class()

    def _connect(self, user):
        """A connection of `user` in the register and the session cookie naming it"""
        connection_id = uuid.uuid4().hex
        self.site.register.siteregister.new_connection(connection_id, user=user)
        secret = self.site.config['secret'] or self.site.site_name
        cookie = MarshalCookie({'user': user, 'connection_id': connection_id,
                                'data': {}, 'locale': None}, secret)
        return connection_id, cookie.output()

    def _open_page(self, user, connection_id):
        """A page of `user` alive in the register, as the one that built the url"""
        page_id = uuid.uuid4().hex
        self.site.register.siteregister.new_page(page_id, pagename='index',
                                                 connection_id=connection_id,
                                                 user=user, data=Bag())
        return page_id

    def _get(self, pkey=None, cookie=None, **query):
        path = f'/sys/ep_table/adm/htmltemplate_atc/{pkey or self.pkey}/get/filepath'
        builder = EnvironBuilder(method='GET', base_url=self.site.external_host, path=path,
                                 query_string=query)
        if cookie:
            builder.headers['Cookie'] = f'{self.site.currentDomainIdentifier}={cookie}'
        request = Request(builder.get_environ())
        response = Response()
        page = self.site.resource_loader(path.strip('/').split('/'), request, response,
                                         request_kwargs=dict(request.args))
        self.site.currentPage = page
        body = page()
        return response.status_code, body

    def test_logged_user_reads_the_document_without_a_page(self):
        _, cookie = self._connect('ep_alice')
        status, body = self._get(cookie=cookie)
        assert status == 200
        assert body == CONTENT.encode()

    def test_url_outlives_the_page_that_built_it(self):
        _, cookie = self._connect('ep_alice')
        status, body = self._get(cookie=cookie, _current_page_id='closed_page_id')
        assert status == 200
        assert body == CONTENT.encode()

    def test_page_id_is_not_a_bearer_token(self):
        connection_id, _ = self._connect('ep_alice')
        page_id = self._open_page('ep_alice', connection_id)
        status, body = self._get(_current_page_id=page_id)
        assert status == 403
        assert body == ''

    def _datachanges(self, page_id):
        return self.site.register.siteregister.page_register.get_datachanges(page_id)

    def test_own_page_still_gets_the_record_refresh(self):
        connection_id, cookie = self._connect('ep_alice')
        page_id = self._open_page('ep_alice', connection_id)
        status, _ = self._get(cookie=cookie, _current_page_id=page_id)
        assert status == 200
        assert self._datachanges(page_id)

    def test_another_users_page_gets_nothing(self):
        connection_id, _ = self._connect('ep_alice')
        page_id = self._open_page('ep_alice', connection_id)
        _, cookie = self._connect('ep_bob')
        status, body = self._get(cookie=cookie, _current_page_id=page_id)
        assert status == 200
        assert body == CONTENT.encode()
        assert not self._datachanges(page_id)

    def test_cookie_of_an_expired_connection_is_refused(self):
        connection_id, cookie = self._connect('ep_alice')
        self.site.register.siteregister.drop_connection(connection_id)
        status, _ = self._get(cookie=cookie)
        assert status == 403

    def test_read_tags_are_checked_on_the_logged_user(self, monkeypatch):
        colattr = self.db.table('adm.htmltemplate_atc').column('filepath').attributes
        monkeypatch.setitem(colattr, 'readTags', 'ep_reader')
        _, cookie = self._connect('ep_alice')
        assert self._get(cookie=cookie)[0] == 403
        _, cookie = self._connect('ep_carol')
        status, body = self._get(cookie=cookie)
        assert status == 200
        assert body == CONTENT.encode()

    def test_missing_file_answers_404(self):
        _, cookie = self._connect('ep_alice')
        status, body = self._get(pkey=self.missing_pkey, cookie=cookie)
        assert status == 404
        assert body == ''

    def test_no_session_is_refused(self):
        status, body = self._get()
        assert status == 403
        assert body == ''
