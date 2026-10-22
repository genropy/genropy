"""Docs as MyST Markdown in the `inlinedoc` storage, served by sys/ep_doc.

Runs on a real GnrDummySite over the isolated ``gnrtest`` instance (sys, adm),
with the inlinedoc experimental flag on: with no `inlinedoc` service configured
the docs are a real `inlinedoc` folder of the instance, users and tags are adm
records. Replaced: the page register (the daemon's), the connection id and the
HTTP method of the dummy page's request, and boto's paginator for aws_s3.
"""

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.wrappers import Response

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport, instanceMixin
from gnr.lib.services.storage import StorageService
from gnr.web import gnrdocumentation
from gnr.web.gnrdocumentation import (DocumentationConflict, DocumentationStore, doc_folder,
                                      join_front_matter, render_markdown, split_front_matter)
from gnr.web.gnrdummysite import GnrDummySite

ROOT = Path(__file__).resolve().parents[3]
ep_doc = gnrImport(str(ROOT / 'projects' / 'gnrcore' / 'packages' / 'sys' / 'webpages' / 'ep_doc.py'),
                   avoidDup=True)
aws_s3 = gnrImport(str(ROOT / 'projects' / 'gnrcore' / 'packages' / 'sys' / 'resources' / 'services'
                       / 'storage' / 'aws_s3.py'), avoidDup=True)
PNG = 'data:image/png;base64,iVBORw0KGgo='
CONNECTION = 'C_PROBE'


class WithMethod(object):
    """The dummy page's request, as a request of the given HTTP method"""

    def __init__(self, request, method):
        self._request = request
        self.method = method

    def __getattr__(self, name):
        return getattr(self._request, name)


@pytest.mark.parametrize('address, folder', [
    ('package:adm:', 'adm/_package'),
    ('table:adm.user:', 'adm/user/_table'),
    ('field:adm.user:username', 'adm/user/fields/username'),
    ('grouplet:adm.user:contacts', 'adm/user/grouplets/contacts'),
    ('grouplet:test:topic/card', 'test/_grouplets/topic/card'),
    ('page:test/orders:delivery', 'test/_pages/orders/delivery'),
])
def test_an_address_has_one_folder(address, folder):
    assert doc_folder(address) == folder


@pytest.mark.parametrize('address', ['field:../etc:x', 'grouplet:test:../x', 'field:adm.user:a/b',
                                     'field:adm:username', 'table:adm:', 'page:test:x', 'nokind:a:b',
                                     'field:adm.user', '', None])
def test_anything_else_is_refused(address):
    with pytest.raises(ValueError):
        doc_folder(address)


def test_front_matter_round_trip():
    text = join_front_matter({'id': 'field:adm.user:username', 'title': 'Città'}, '\n\nBody')
    assert text == '---\nid: field:adm.user:username\ntitle: Città\n---\n\nBody'
    assert split_front_matter(text) == ({'id': 'field:adm.user:username', 'title': 'Città'}, 'Body')
    assert split_front_matter('No front matter') == ({}, 'No front matter')


def test_markdown_renders_tables_and_images_but_no_markup():
    html = render_markdown('<script>x</script> [a](javascript:alert(1)) ![m](assets/a.png)\n\n'
                           '|a|\n|-|\n|$city|', lambda name: f'/sys/ep_doc?asset={name}&p=1')
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'href="javascript:' not in html, 'left as text, not a link'
    assert '<img src="/sys/ep_doc?asset=a.png&amp;p=1" alt="m" />' in html
    assert '<td>$city</td>' in html, 'the variables are left for the caller'


class S3Listing(aws_s3.Service):
    """aws_s3 with boto's paginator replaced: no S3 is reachable from the tests"""

    def __init__(self, pages):
        self.bucket = 'docs'
        self.base_path = 'app'
        self.pages = pages

    @property
    def _client(self):
        pages = self.pages

        class Paginator:
            def paginate(self, Bucket, Prefix):
                self.prefix = Prefix
                return SimpleNamespace(search=lambda key: (item for page in pages for item in page.get(key) or [None]))
        return SimpleNamespace(get_paginator=lambda name: Paginator())


def test_aws_s3_lists_every_page_with_its_mtimes():
    stamp = datetime(2026, 10, 22, tzinfo=timezone.utc)
    service = S3Listing([{'Contents': [{'Key': 'app/adm/user/fields/username/it.md', 'LastModified': stamp}]},
                         {},
                         {'Contents': [{'Key': 'app/adm/user/.gnrdir', 'LastModified': stamp},
                                       {'Key': 'app/adm/user/_table/en.md', 'LastModified': stamp}]}])
    assert service.file_mtimes('adm/user') == {'fields/username/it.md': stamp.timestamp(),
                                               '_table/en.md': stamp.timestamp()}


class TestDocumentation(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        db = cls.site.db
        tag = db.table('adm.htag').newrecord(code='doc_adm', description='Documents adm')
        db.table('adm.htag').insert(tag)
        users = {}
        for username in ('writer', 'reader'):
            user = db.table('adm.user').newrecord(username=username, firstname=username,
                                                  lastname='Probe', email=f'{username}@example.org')
            db.table('adm.user').insert(user)
            users[username] = user['id']
        db.table('adm.user_tag').insert(db.table('adm.user_tag').newrecord(user_id=users['writer'],
                                                                           tag_id=tag['id']))
        db.commit()
        page_items = dict(P_WRITER=dict(user='writer'), P_READER=dict(user='reader'),
                          P_GUEST=dict(user='guest_123'))
        for page_item in page_items.values():
            page_item['connection_id'] = CONNECTION
        page_items['P_ELSEWHERE'] = dict(user='writer', connection_id='C_OTHER')
        cls.site.register.page = lambda page_id, include_data=None: page_items.get(page_id)
        cls.site.gnrapp.config.setItem('experimental.gui', None, inlinedoc='true')
        cls.folder = os.path.join(cls.site.gnrapp.instanceFolder, 'inlinedoc')

    def setup_method(self):
        shutil.rmtree(self.folder, ignore_errors=True)
        self.site.doc_listings.clear()
        self.store = DocumentationStore(self.site)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)
        super().teardown_class()

    def endpoint(self, method='GET'):
        page = self.site.dummyPage
        page.mixinComponent('gnrcomponents/externalcall:EndpointPermission')
        instanceMixin(page, ep_doc.GnrCustomWebPage)
        page.request = WithMethod(page.request, method)
        page.connection.connection_id = CONNECTION
        return page

    def call(self, page_id='P_READER', method='GET', **kwargs):
        result = self.endpoint(method).rootPage(_calling_page_id=page_id, **kwargs)
        return json.loads(result) if isinstance(result, str) and result.startswith('{') else result

    def write(self, relpath, text):
        path = os.path.join(self.folder, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

    def test_module_under_test(self):
        assert gnrdocumentation.__file__.startswith(str(ROOT))
        assert ep_doc.__file__.startswith(str(ROOT))

    def test_without_an_inlinedoc_service_the_docs_go_in_the_instance(self):
        assert self.store.root == 'inlinedoc:'
        assert not self.folder.startswith(self.site.site_static_dir + os.sep), 'not under the served folder'
        self.store.save('field:adm.user:username', 'it', 'Il *nome* di login', title='Username',
                        author='writer')
        with open(os.path.join(self.folder, 'adm/user/fields/username/it.md'), encoding='utf-8') as f:
            meta, body = split_front_matter(f.read())
        assert body == 'Il *nome* di login'
        assert (meta['id'], meta['title'], meta['type'], meta['author']) == \
            ('field:adm.user:username', 'Username', 'reference', 'writer')
        assert meta['updated']

    def test_a_configured_inlinedoc_service_takes_the_docs(self, tmp_path):
        service = self.site.db.table('sys.service')
        record = service.newrecord(service_type='storage', service_name='inlinedoc', implementation='local',
                                   parameters=Bag(dict(base_path=str(tmp_path))))
        service.insert(record)
        self.site.db.commit()
        self.site.storage_handler.updateStorageParams('inlinedoc')
        try:
            assert self.store.root == 'inlinedoc:'
            self.store.save('field:adm.user:username', 'it', 'Login')
            assert (tmp_path / 'adm/user/fields/username/it.md').exists()
            assert not os.path.exists(self.folder), 'the instance folder is not used'
        finally:
            service.delete(record)
            self.site.db.commit()
            self.site.storage_handler.removeStorageFromCache('inlinedoc')
        self.store.save('field:adm.user:username', 'it', 'Login', force=True)
        assert os.path.exists(os.path.join(self.folder, 'adm/user/fields/username/it.md')), \
            'back in the instance folder'

    def test_no_url_serves_the_docs(self):
        self.store.save('field:adm.user:username', 'en', 'Login')
        handler = self.site.storage_handler
        assert handler.isPrivateStorage('inlinedoc') and not handler.isPrivateStorage('home')
        def status(path_list):
            answers = []
            self.site.storageDispatcher(path_list, {'REQUEST_METHOD': 'GET'},
                                        lambda status, headers, *args: answers.append(status))
            return answers[0]
        assert status(['_storage', 'inlinedoc', 'adm', 'user', 'fields', 'username', 'en.md']).startswith('404')
        assert status(['inlinedoc:adm', 'user', 'fields', 'username', 'en.md']).startswith('404')
        probe = self.site.storageNode('home:inlinedoc_probe.txt')
        with probe.open('wb') as f:
            f.write(b'public')
        try:
            assert status(['_storage', 'home', 'inlinedoc_probe.txt']).startswith('200'), 'home stays served'
        finally:
            probe.delete()

    def test_local_listing_is_recursive_and_the_generic_one_agrees(self):
        self.write('adm/user/fields/username/it.md', 'a')
        self.write('adm/user/fields/username/assets/x.png', 'b')
        self.write('adm/user/_table/en.md', 'c')
        node = self.store.node('adm/user')
        listing = node.file_mtimes()
        assert set(listing) == {'fields/username/it.md', 'fields/username/assets/x.png', '_table/en.md'}
        assert StorageService.file_mtimes(node.service, node.path) == listing

    def test_the_index_picks_the_language_and_lists_each_table_once(self, monkeypatch):
        self.write('adm/user/fields/username/en.md', 'en')
        self.write('adm/user/fields/username/it.md', 'it')
        self.write('adm/user/fields/email/en.md', 'en')
        self.write('adm/user/fields/email/assets/x.png', 'png')
        listed = []
        original = StorageService.file_mtimes

        def counting(node):
            listed.append(node.path)
            return original(node.service, node.path)
        monkeypatch.setattr('gnr.lib.services.storage.StorageNode.file_mtimes', counting)
        index = self.store.index(['field:adm.user:username', 'field:adm.user:email', 'field:adm.user:name',
                                  'table:adm.user:', 'not an address'], ['it', 'en'])
        assert {a: v['language'] for a, v in index.items()} == {'field:adm.user:username': 'it',
                                                                 'field:adm.user:email': 'en'}
        assert listed == ['adm/user'], 'one listing for the whole table'

    def test_a_save_refuses_a_doc_changed_since_it_was_read(self):
        mtime = self.store.save('field:adm.user:email', 'it', 'v1')
        with pytest.raises(DocumentationConflict):
            self.store.save('field:adm.user:email', 'it', 'v2')
        time.sleep(0.01)
        self.store.save('field:adm.user:email', 'it', 'v2', base_mtime=mtime)
        self.store.save('field:adm.user:email', 'it', 'v3', force=True)
        assert self.store.read('field:adm.user:email', ['it'])['markdown'] == 'v3'
        with pytest.raises(ValueError):
            self.store.save('field:adm.user:email', '../x', 'v4', force=True)

    def test_an_empty_doc_is_removed(self):
        mtime = self.store.save('field:adm.user:email', 'it', 'v1')
        assert self.store.save('field:adm.user:email', 'it', '  \n', base_mtime=mtime) is None
        assert self.store.read('field:adm.user:email', ['it']) is None
        assert self.store.index(['field:adm.user:email'], ['it']) == {}

    def test_a_doc_another_process_wrote_is_read_at_once(self):
        assert self.store.index(['field:adm.user:email'], ['it']) == {}, 'the listing is kept'
        self.write('adm/user/fields/email/it.md', 'Written elsewhere')
        doc = self.store.read('field:adm.user:email', ['it'])
        assert doc and doc['markdown'] == 'Written elsewhere', 'a read does not wait for the listing'
        self.store.save('field:adm.user:email', 'it', 'v2', base_mtime=doc['mtime'])

    def test_a_save_refreshes_the_index_at_once(self):
        assert self.store.index(['field:adm.user:email'], ['it']) == {}
        self.store.save('field:adm.user:email', 'it', 'v1')
        assert 'field:adm.user:email' in self.store.index(['field:adm.user:email'], ['it'])

    def test_only_png_jpeg_gif_webp_images_are_stored(self):
        link = self.store.save_asset('field:adm.user:email', PNG)
        assert link.startswith('assets/') and link.endswith('.png')
        assert self.store.asset_node('field:adm.user:email', link[len('assets/'):]).exists
        for data_url in ('data:image/svg+xml;base64,PHN2Zz4=', 'data:text/html;base64,PGI+', 'nothing',
                         'data:image/png;base64,PGI+', 'data:image/png;base64,not base64!'):
            with pytest.raises(ValueError):
                self.store.save_asset('field:adm.user:email', data_url)

    def test_an_image_larger_than_the_limit_is_refused(self, monkeypatch):
        monkeypatch.setattr(gnrdocumentation, 'ASSET_MAX_SIZE', 4)
        with pytest.raises(ValueError):
            self.store.save_asset('field:adm.user:email', PNG)

    def test_only_a_registered_page_of_a_logged_user_from_its_connection(self):
        self.store.save('field:adm.user:username', 'en', 'Login')
        for page_id in (None, 'P_UNKNOWN', 'P_GUEST', 'P_ELSEWHERE'):
            assert isinstance(self.call(page_id, address='field:adm.user:username', _fragment=1), Forbidden)
        assert self.call(address='field:adm.user:username', _fragment=1)['exists'] is True

    def test_the_fragment_renders_the_doc_with_its_images(self):
        self.store.save('field:adm.user:username', 'en', '# Login\n\n![map](assets/a.png) $city',
                        title='Username')
        doc = self.call(address='field:adm.user:username', _fragment=1, language='it')
        assert (doc['title'], doc['language'], doc['editable']) == ('Username', 'en', False)
        assert doc['markdown'].startswith('# Login')
        assert '<h1>Login</h1>' in doc['html'] and '$city' in doc['html']
        assert 'src="/sys/ep_doc?address=field%3Aadm.user%3Ausername&amp;asset=a.png&amp;' \
               '_calling_page_id=P_READER"' in doc['html']

    def test_an_empty_doc_is_offered_to_its_documenter_only(self):
        assert isinstance(self.call(address='field:adm.user:email', _fragment=1), NotFound)
        doc = self.call('P_WRITER', address='field:adm.user:email', _fragment=1, language='it')
        assert (doc['exists'], doc['editable'], doc['markdown'], doc['language']) == (False, True, '', 'it')
        assert isinstance(self.call('P_WRITER', address='field:sys.service:name', _fragment=1), NotFound), \
            'doc_adm documents adm only'

    def test_the_index_tells_existing_and_editable_addresses(self):
        self.store.save('field:adm.user:username', 'en', 'Login')
        addresses = 'field:adm.user:username,field:adm.user:email,field:sys.service:name,junk'
        reader = self.call(_index=1, addresses=addresses, language='it')
        writer = self.call('P_WRITER', _index=1, addresses=addresses, language='it')
        assert list(reader['docs']) == ['field:adm.user:username'] == list(writer['docs'])
        assert reader['editable'] == []
        assert writer['editable'] == ['field:adm.user:username', 'field:adm.user:email']

    def test_saving_needs_post_and_the_documenter_tag(self):
        kwargs = dict(_save=1, address='field:adm.user:email', markdown='Mail', title='Email', language='it')
        assert isinstance(self.call('P_READER', method='POST', **kwargs), Forbidden)
        assert isinstance(self.call('P_WRITER', **kwargs), NotFound), 'a GET writes nothing'
        saved = self.call('P_WRITER', method='POST', **kwargs)
        doc = self.store.read('field:adm.user:email', ['it'])
        assert doc['markdown'] == 'Mail' and doc['mtime'] == saved['mtime']
        assert doc['meta']['author'] == 'writer'
        stale = self.call('P_WRITER', method='POST', **dict(kwargs, markdown='Other'))
        assert isinstance(stale, Response) and stale.status_code == 409
        assert self.call('P_WRITER', method='POST', **dict(kwargs, markdown='Other', force='1'))['mtime']

    def test_an_image_is_stored_by_its_documenter_and_served_to_the_reader(self):
        result = self.call('P_WRITER', method='POST', _asset=1, address='field:adm.user:email', dataUrl=PNG)
        name = result['link'][len('assets/'):]
        assert self.call(address='field:adm.user:email', asset=name).startswith(b'\x89PNG')
        assert isinstance(self.call(address='field:adm.user:email', asset='missing.png'), NotFound)
        assert isinstance(self.call(address='field:adm.user:email', asset='../it.md'), NotFound)
        assert isinstance(self.call('P_READER', method='POST', _asset=1, address='field:adm.user:email',
                                    dataUrl=PNG), Forbidden)

    def test_the_page_of_a_doc_blanks_its_variables(self):
        self.store.save('grouplet:adm.user:contacts', 'en', 'Goods for **$city**', title='Contacts')
        page = self.call(address='grouplet:adm.user:contacts', language='en')
        assert '<title>Contacts</title>' in page
        assert '<p>Goods for <strong></strong></p>' in page
        assert isinstance(self.call(address='grouplet:adm.user:missing'), NotFound)
        assert isinstance(self.call(address='nokind:a:b', _fragment=1), NotFound)

    def test_off_without_the_experimental_flag(self):
        self.store.save('field:adm.user:username', 'en', 'Login')
        config = self.site.gnrapp.config
        config.setAttr('experimental.gui', inlinedoc='false')
        try:
            assert isinstance(self.call(address='field:adm.user:username', _fragment=1), NotFound)
        finally:
            config.setAttr('experimental.gui', inlinedoc='true')
