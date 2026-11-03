"""Attachment tables read outside a web site (#493).

``adm.htmltemplate_atc`` is an ``AttachmentTable``: its static pyColumn
``fileurl`` used to read ``application.site`` unguarded, so any fetch from a
plain ``GnrApp`` (``gnr app cleanup`` cascading through ``deleteRelated``)
raised AttributeError.

The retention cleanup runs on a ``GnrDummySite``, like ``gnr app cleanup``,
so the cascaded delete of the attachments also removes their stored files.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import getUuid
from gnr.web.gnrdummysite import GnrDummySite


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


class TestAttachmentRetentionCleanup(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name)
        cls.db = cls.site.gnrapp.db
        cls.tblobj = cls.db.table('adm.htmltemplate_atc')

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'db', None):
            cls.db.closeConnection()
        super().teardown_class()

    def test_retention_deletes_attachment_and_file(self):
        letterhead_tbl = self.db.table('adm.htmltemplate')
        letterhead = letterhead_tbl.newrecord(name='letterhead %s' % getUuid())
        letterhead_tbl.insert(letterhead)
        filepath = 'retention_test/%s.txt' % getUuid()
        attachment_node = self.site.storageNode('home:%s' % filepath)
        with attachment_node.open(mode='w') as attachment:
            attachment.write('attached content')
        record = self.tblobj.newrecord(filepath=filepath, description='attachment',
                                       maintable_id=letterhead['id'])
        self.tblobj.insert(record)
        self.db.commit()
        assert attachment_node.exists
        # past cutoff, restricted to this letterhead
        policy = dict(filter_column='__ins_ts', retention_period=-1,
                      extra_where_filter="$id='%s'" % letterhead['id'])
        report = letterhead_tbl.executeRetentionPolicy(policy=policy, dry_run=False)
        assert report == dict(found_records=1, deleted_records=1)
        assert not self.tblobj.query(where='$id=:pkey', pkey=record['id'],
                                     excludeLogicalDeleted=False).count()
        assert not attachment_node.exists
