"""Attachment tables read outside a web site (#493).

``adm.htmltemplate_atc`` is an ``AttachmentTable``: its static pyColumn
``fileurl`` used to read ``application.site`` unguarded, so any fetch from a
plain ``GnrApp`` (``gnr app cleanup`` cascading through ``deleteRelated``)
raised AttributeError.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import getUuid


class TestAttachmentNoSite(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.app = GnrApp(cls.test_instance_name)
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.db.commit()
        cls.tblobj = cls.db.table('adm.htmltemplate_atc')

    def setup_method(self):
        letterhead_tbl = self.db.table('adm.htmltemplate')
        self.letterhead = letterhead_tbl.newrecord(name='letterhead %s' % getUuid())
        letterhead_tbl.insert(self.letterhead)
        filepaths = ('home:no_site/%s.txt' % getUuid(), 'no_site/%s.txt' % getUuid())
        self.records = [self.tblobj.newrecord(filepath=filepath, description='attachment',
                                              maintable_id=self.letterhead['id'])
                        for filepath in filepaths]
        for record in self.records:
            self.tblobj.insert(record)
        self.db.commit()

    def test_app_has_no_site(self):
        assert not hasattr(self.app, 'site')

    def test_fileurl_without_site(self):
        for record in self.records:
            fetched = self.tblobj.record(pkey=record['id']).output('dict')
            assert fetched['fileurl'] is None

    def test_delete_master_cascades_without_site(self):
        letterhead_tbl = self.db.table('adm.htmltemplate')
        letterhead = letterhead_tbl.record(pkey=self.letterhead['id'], for_update=True).output('dict')
        letterhead_tbl.delete(letterhead)
        self.db.commit()
        assert not self.tblobj.query(where='$maintable_id=:m', m=self.letterhead['id'],
                                     excludeLogicalDeleted=False).count()
