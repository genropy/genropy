"""Real checks on the ``archive_and_delete`` resource action (#836).

The batch is loaded through the site resource loader and its steps are run
against the ``gnrtest`` instance, so the assertions look at the real
``export_archive`` tree on disk and at the real records in the database.

``adm.htmltemplate_atc`` is the fixture table: it is an ``AttachmentTable``,
so it exercises the ``onArchiveExport`` branch of ``step_archive`` on the
archived table itself, and it carries ``__del_ts``, so it also covers the
logically deleted records the batch is expected to archive and delete.
"""

import os
import shutil
import sys
from datetime import datetime

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import getUuid
from gnr.web.gnrdummysite import GnrDummySite

TABLE = 'adm.htmltemplate_atc'
RESPATH = 'action/_common/archive_and_delete'
ARCHIVE_NAME = 'test_archive'


class TestArchiveAndDelete(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.db = cls.site.db
        cls.tblobj = cls.db.table(TABLE)
        cls.export_archive = cls.site.getStaticPath('vol:export_archive')

    def setup_method(self):
        """Start every test from an empty export_archive and one stored attachment"""
        shutil.rmtree(self.export_archive, ignore_errors=True)
        letterhead_tbl = self.db.table('adm.htmltemplate')
        self.letterhead = letterhead_tbl.newrecord(name='letterhead %s' % getUuid())
        letterhead_tbl.insert(self.letterhead)
        self.filepath = 'archive_and_delete_test/%s.txt' % getUuid()
        self.attachment_node = self.site.storageNode('home:%s' % self.filepath)
        with self.attachment_node.open(mode='w') as attachment:
            attachment.write('attached content')
        self.record = self.tblobj.newrecord(filepath=self.filepath, description='attachment',
                                            maintable_id=self.letterhead['id'])
        self.tblobj.insert(self.record)
        self.db.commit()

    def buildBatch(self, **batch_parameters):
        batch = self.site.loadTableScript(page=self.site.dummyPage, table=TABLE, respath=RESPATH)
        batch.batch_parameters = batch_parameters
        batch.selectedPkeys = [self.record['id']]
        return batch

    def runBatch(self, **batch_parameters):
        batch = self.buildBatch(**batch_parameters)
        for step in batch.batch_steps.split(','):
            getattr(batch, 'step_%s' % step)()
        return batch

    def sourceFolder(self, name=ARCHIVE_NAME):
        return os.path.join(self.export_archive, 'source', name)

    def recordExists(self):
        return self.tblobj.query(where='$%s=:pkey' % self.tblobj.pkey, pkey=self.record['id'],
                                 excludeLogicalDeleted=False, excludeDraft=False).count()

    def logicalDelete(self):
        record = self.tblobj.record(pkey=self.record['id'], for_update=True).output('dict')
        old_record = dict(record)
        record[self.tblobj.logicalDeletionField] = datetime.now()
        self.tblobj.update(record, old_record)
        self.db.commit()

    def test_resource_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure the
        # resource being exercised is the one in this working tree
        checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        batch = self.buildBatch(mode='D')
        resource_file = sys.modules[type(batch).__module__].__file__
        assert resource_file.startswith(checkout + os.sep)

    def test_delete_only_creates_no_folder(self):
        self.runBatch(mode='D')
        assert not os.path.exists(self.export_archive)

    def test_delete_only_deletes_the_records(self):
        self.runBatch(mode='D')
        assert self.recordExists() == 0

    def test_archive_only_keeps_the_records(self):
        self.runBatch(mode='A', name=ARCHIVE_NAME)
        assert self.recordExists() == 1

    def test_archive_writes_the_pickle_beside_no_records_folder(self):
        self.runBatch(mode='A', name=ARCHIVE_NAME)
        source_folder = self.sourceFolder()
        assert os.path.isfile(os.path.join(source_folder, 'records.pik'))
        # records is the basename of the pickled bag: it must not also exist as a folder
        assert not os.path.exists(os.path.join(source_folder, 'records'))
        assert os.path.isfile(os.path.join(self.export_archive, 'results',
                                           '%s.zip' % ARCHIVE_NAME))

    def test_archive_holds_the_selected_records(self):
        self.runBatch(mode='A', name=ARCHIVE_NAME)
        archive = Bag(os.path.join(self.sourceFolder(), 'records.pik'))
        archived = archive[TABLE.replace('.', '/')]
        assert [r['id'] for r in archived] == [self.record['id']]

    def test_archive_copies_the_attachments_of_the_archived_table(self):
        self.runBatch(mode='A', name=ARCHIVE_NAME)
        copied = os.path.join(self.sourceFolder(), 'files', TABLE, self.record['id'],
                              os.path.basename(self.filepath))
        assert os.path.isfile(copied)
        with open(copied, encoding='utf-8') as attachment:
            assert attachment.read() == 'attached content'

    def test_missing_attachment_leaves_no_empty_files_folder(self):
        self.attachment_node.delete()
        self.runBatch(mode='A', name=ARCHIVE_NAME)
        assert not os.path.exists(os.path.join(self.sourceFolder(), 'files'))

    def test_logically_deleted_records_are_archived_and_deleted(self):
        self.logicalDelete()
        self.runBatch(mode='AD', name=ARCHIVE_NAME)
        archive = Bag(os.path.join(self.sourceFolder(), 'records.pik'))
        assert [r['id'] for r in archive[TABLE.replace('.', '/')]] == [self.record['id']]
        assert self.recordExists() == 0

    def test_result_handler_reports_the_zip_only_when_archiving(self):
        delete_only = self.runBatch(mode='D')
        assert delete_only.result_handler() == ('Completed', None)
        archiving = self.runBatch(mode='A', name=ARCHIVE_NAME)
        result, result_attr = archiving.result_handler()
        assert result_attr['url'].endswith('/%s.zip' % ARCHIVE_NAME)
