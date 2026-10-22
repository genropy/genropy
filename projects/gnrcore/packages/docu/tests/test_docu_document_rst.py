"""docu.documentation.documentRst: the title and rst a page is read with,
shared by docu/index/rst and the docu: kind of sys/ep_doc.

Runs on a real database built from the gnrdevelop instance (with docu).
"""
from gnr.core.gnrbag import Bag

from core.common import BaseGnrAppTest


class TestDocumentRst(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.doctbl = cls.db.table('docu.documentation')
        root = dict(name='rstguide')
        cls.doctbl.insert(root)
        for name, docbag in (('bilingual', {'it.title': 'Installare', 'it.rst': 'Testo italiano',
                                            'en.title': 'Install', 'en.rst': 'English text'}),
                             ('english', {'en.title': 'Only english', 'en.rst': 'English only'}),
                             ('empty', {})):
            bag = Bag()
            for path, value in docbag.items():
                bag[path] = value
            cls.doctbl.insert(dict(name=name, parent_id=root['id'], docbag=bag))
        cls.db.commit()

    def test_the_reader_language_first(self):
        assert self.doctbl.documentRst('rstguide/bilingual', language='it') == \
            dict(title='Installare', rst='Testo italiano')
        assert self.doctbl.documentRst('rstguide/bilingual', language='en') == \
            dict(title='Install', rst='English text')

    def test_english_then_italian_when_the_language_is_missing(self):
        assert self.doctbl.documentRst('rstguide/english', language='it') == \
            dict(title='Only english', rst='English only')

    def test_an_empty_page_takes_the_placeholder_and_its_name(self):
        assert self.doctbl.documentRst('rstguide/empty', placeholder='To do...') == \
            dict(title='rstguide/empty', rst='To do...')

    def test_a_missing_page_is_none(self):
        assert self.doctbl.documentRst('rstguide/missing') is None
