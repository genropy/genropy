"""sys/ep_doc: one address for the docs of grouplets, field helpers and handbook pages.

Runs on a real GnrDummySite over the isolated ``gnrtest`` instance (sys, adm):
the grouplet resources and their doc file live in its throwaway site folder,
the helper file is written by the page's own ``saveHelperValue``, users and
tags are adm records. Only the page register is replaced: it is the daemon's.
"""

import json
import os
import shutil
from pathlib import Path

from werkzeug.exceptions import Forbidden, NotFound

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import gnrImport, instanceMixin
from gnr.web.gnrdummysite import GnrDummySite

ROOT = Path(__file__).resolve().parents[3]
ep_doc = gnrImport(str(ROOT / 'projects' / 'gnrcore' / 'packages' / 'sys' / 'webpages' / 'ep_doc.py'),
                   avoidDup=True)

GROUPLET = '''
from gnr.web.gnrbaseclasses import BaseComponent

class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Doc probe', card=%s)

    def grouplet_main(self, pane, **kwargs):
        pane.div('probe')
'''
DOC_HTML = '<p>$city leaves with $courier</p><img src="doc_probe.svg">'
HELPER_TABLE = 'adm.user'
HELPER_NAME = 'th_user_DocProbe'


class TestDocEndpoint(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        folder = os.path.join(cls.site.site_path, '_resources', 'grouplets')
        os.makedirs(folder, exist_ok=True)
        cards = dict(doc_probe=dict(doc='file:doc_probe.html', doc_kw=dict(courier='Fast Parcel')),
                     doc_restricted=dict(doc='<p>Internal</p>', doc_tags='docreader'),
                     doc_none=dict(collapsible=True))
        for name, card in cards.items():
            with open(os.path.join(folder, f'{name}.py'), 'w') as f:
                f.write(GROUPLET % repr(card))
        with open(os.path.join(folder, 'doc_probe.html'), 'w') as f:
            f.write(DOC_HTML)
        with open(os.path.join(folder, 'doc_probe.svg'), 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg"/>')
        db = cls.site.db
        tag = db.table('adm.htag').newrecord(code='docreader', description='Doc reader')
        db.table('adm.htag').insert(tag)
        users = {}
        for username in ('reader', 'plain'):
            user = db.table('adm.user').newrecord(username=username, firstname=username,
                                                  lastname='Probe', email=f'{username}@example.org')
            db.table('adm.user').insert(user)
            users[username] = user['id']
        db.table('adm.user_tag').insert(db.table('adm.user_tag').newrecord(user_id=users['reader'],
                                                                           tag_id=tag['id']))
        db.commit()
        page_items = dict(P_READER=dict(user='reader'), P_PLAIN=dict(user='plain'),
                          P_GUEST=dict(user='guest_123'))
        cls.site.register.page = lambda page_id, include_data=None: page_items.get(page_id)
        cls.helper_folder = cls.site.dummyPage.packageResourcePath(HELPER_TABLE, 'helper')
        cls.helper_folder_existed = os.path.isdir(cls.helper_folder)

    @classmethod
    def teardown_class(cls):
        helper_file = os.path.join(cls.helper_folder, f'{HELPER_NAME}.xml')
        if os.path.exists(helper_file):
            os.remove(helper_file)
        if not cls.helper_folder_existed and os.path.isdir(cls.helper_folder):
            shutil.rmtree(cls.helper_folder)
        super().teardown_class()

    def endpoint(self):
        page = self.site.dummyPage
        page.mixinComponent('gnrcomponents/externalcall:EndpointPermission')
        page.mixinComponent('gnrcomponents/grouplet/grouplet:GroupletHandler')
        instanceMixin(page, ep_doc.GnrCustomWebPage)
        return page

    def fragment(self, address, page_id='P_PLAIN', **kwargs):
        result = self.endpoint().rootPage(address=address, _fragment=1, _calling_page_id=page_id, **kwargs)
        return json.loads(result) if isinstance(result, str) else result

    def test_module_under_test(self):
        assert ep_doc.__file__.startswith(str(ROOT))

    def test_only_a_registered_page_of_a_logged_user(self):
        for page_id in (None, 'P_UNKNOWN', 'P_GUEST'):
            assert isinstance(self.fragment('grouplet:sys:doc_probe', page_id=page_id), Forbidden)
        assert self.fragment('grouplet:sys:doc_probe')['title'] == 'Doc probe'

    def test_grouplet_fragment_is_the_template_with_resource_urls(self):
        doc = self.fragment('grouplet:sys:doc_probe')
        assert '$city leaves with $courier' in doc['html']
        assert 'src="doc_probe.svg"' not in doc['html']
        assert 'doc_probe.svg"' in doc['html']

    def test_grouplet_page_fills_doc_kw_and_blanks(self):
        page = self.endpoint().rootPage(address='grouplet:sys:doc_probe', _calling_page_id='P_PLAIN')
        assert '<title>Doc probe</title>' in page
        assert '<p> leaves with Fast Parcel</p>' in page

    def test_doc_tags_restrict_the_doc(self):
        assert isinstance(self.fragment('grouplet:sys:doc_restricted'), Forbidden)
        assert self.fragment('grouplet:sys:doc_restricted', page_id='P_READER')['html'] == '<p>Internal</p>'

    def test_unknown_addresses_are_not_found(self):
        for address in ('grouplet:sys:doc_none', 'grouplet:sys:missing', 'nokind:a:b', 'grouplet',
                        'docu::guide/install', 'help:adm:code', None):
            assert isinstance(self.fragment(address), NotFound), address

    def test_help_saved_by_the_developer_is_served_escaped(self):
        page = self.endpoint()
        page.saveHelperValue(table=HELPER_TABLE, name=HELPER_NAME, helpcode='nickname',
                             value='Leave <it>\nhere\n\nat the door')
        doc = self.fragment('help:adm.user/DocProbe:nickname', language=page.language)
        assert doc['html'] == '<p>Leave &lt;it&gt;<br>here</p><p>at the door</p>'
        assert isinstance(self.fragment('help:adm.user/DocProbe:nickname', language='xx'), NotFound)
        assert isinstance(self.fragment('help:adm.user/DocProbe:other', language=page.language), NotFound)

    def test_page_side_card_carries_the_address_not_the_doc(self):
        page = self.endpoint()
        card = page._gr_cardInfo(resource='doc_probe')
        assert card['doc_address'] == f'grouplet:{page.package.name}:doc_probe'
        assert 'doc' not in card
        assert card['doc_kw'] == dict(courier='Fast Parcel')
        assert 'doc_address' not in page._gr_cardInfo(resource='doc_none')
