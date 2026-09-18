"""Tests for the example-module synchronization of docu.documentation.

The .py example files served from site:webpages/docu_examples must follow
the record lifecycle: written when the sourcebag changes, relocated when
the record is renamed or moved in the hierarchy (keeping the folders of
the children records intact), removed when the record is deleted, and
regenerable in bulk from the sourcebag since the site folder is
disposable. The rst links pointing to a renamed record must be rewritten
in the docbag of the other records.

The tests need no running site nor a shared database: they build a
throwaway application on a temporary sqlite file and expose a real local
storage service on a temporary directory, so the records go through the
actual table triggers and the assertions read the actual filesystem.
"""
import os
import shutil
import tempfile
from types import SimpleNamespace

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.lib.services.storage import BaseLocalService, StorageNode


class StorageSiteStub:
    """Minimal site wiring exposing a real local storage service to the model."""

    def __init__(self, services_dirs):
        self.currentPage = SimpleNamespace(isMobile=False, user=None)
        self.services = {}
        for name, base_path in services_dirs.items():
            service = BaseLocalService(parent=self, base_path=base_path)
            service.service_name = name
            self.services[name] = service

    def storageNode(self, fullpath, *parts):
        if parts:
            fullpath = '/'.join([fullpath] + list(parts))
        service_name, path = fullpath.split(':', 1)
        return StorageNode(parent=self, path=path, service=self.services[service_name])


def sourceBag(*versions):
    result = Bag()
    for version, source in versions:
        result.setItem(version, Bag(dict(version=version, source=source)))
    return result


class TestDocuExamplesSync(object):

    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get('GNR_TESTING_INSTANCE_NAME') or 'gnrdevelop'
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_docu_examples_')
        cls.app = GnrApp(cls.instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls.temp_dir, 'testing')))
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.doctbl = cls.db.table('docu.documentation')
        cls.site_dir = tempfile.mkdtemp(prefix='gnr_docu_site_')
        cls.app.site = StorageSiteStub({'site': cls.site_dir})

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        for folder in (cls.site_dir, cls.temp_dir):
            shutil.rmtree(folder, ignore_errors=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def examplesNode(self, hierarchical_name):
        return self.app.site.storageNode('site:webpages/docu_examples/%s'
                                         % hierarchical_name)

    def exampleFiles(self, hierarchical_name):
        """Sorted example file names, or None if the folder is missing."""
        node = self.examplesNode(hierarchical_name)
        if not node.exists:
            return None
        return sorted(n.basename for n in node.children() if not n.isdir)

    def exampleSource(self, hierarchical_name, filename):
        with self.examplesNode(hierarchical_name).child(filename).open('r') as f:
            return f.read()

    def addDoc(self, name, parent_id=None, sourcebag=None, docbag=None):
        record = dict(name=name, parent_id=parent_id)
        self.doctbl.insert(record)
        if sourcebag is not None or docbag is not None:
            with self.doctbl.recordToUpdate(record['id']) as rec:
                if sourcebag is not None:
                    rec['sourcebag'] = sourcebag
                if docbag is not None:
                    rec['docbag'] = docbag
        self.db.commit()
        return record['id']

    def updateDoc(self, pkey, **values):
        with self.doctbl.recordToUpdate(pkey) as rec:
            rec.update(values)
        self.db.commit()

    # ------------------------------------------------------------------
    # sourcebag lifecycle
    # ------------------------------------------------------------------

    def test_write_on_sourcebag_update(self):
        self.addDoc('intro', sourcebag=sourceBag(('v000', "print('first')"),
                                                 ('v010', "print('second')")))
        assert self.exampleFiles('intro') == ['v000.py', 'v010.py']
        assert self.exampleSource('intro', 'v000.py') == "print('first')"

    def test_rename_relocates_files(self):
        pkey = self.addDoc('old_page', sourcebag=sourceBag(('v000', "print('x')")))
        assert self.exampleFiles('old_page') == ['v000.py']
        self.updateDoc(pkey, name='new_page')
        assert self.exampleFiles('old_page') is None
        assert self.exampleFiles('new_page') == ['v000.py']

    def test_move_relocates_files(self):
        shelf_id = self.addDoc('shelf')
        pkey = self.addDoc('orphan', sourcebag=sourceBag(('v000', "print('x')")))
        self.updateDoc(pkey, parent_id=shelf_id)
        assert self.exampleFiles('orphan') is None
        assert self.exampleFiles('shelf/orphan') == ['v000.py']

    def test_parent_rewrite_keeps_children_files(self):
        guide_id = self.addDoc('guide', sourcebag=sourceBag(('v000', "print('guide')")))
        self.addDoc('step', parent_id=guide_id,
                    sourcebag=sourceBag(('v000', "print('step')")))
        self.updateDoc(guide_id, sourcebag=sourceBag(('v000', "print('guide!')"),
                                                     ('v010', "print('more')")))
        assert self.exampleFiles('guide') == ['v000.py', 'v010.py']
        assert self.exampleSource('guide', 'v000.py') == "print('guide!')"
        assert self.exampleFiles('guide/step') == ['v000.py']

    def test_rename_parent_cascades_to_children(self):
        book_id = self.addDoc('book', sourcebag=sourceBag(('v000', "print('book')")))
        self.addDoc('chapter', parent_id=book_id,
                    sourcebag=sourceBag(('v000', "print('chapter')")))
        self.updateDoc(book_id, name='volume')
        assert self.examplesNode('book').exists is False
        assert self.exampleFiles('volume') == ['v000.py']
        assert self.exampleFiles('volume/chapter') == ['v000.py']

    def test_delete_removes_files(self):
        pkey = self.addDoc('trash', sourcebag=sourceBag(('v000', "print('x')")))
        assert self.exampleFiles('trash') == ['v000.py']
        record = self.doctbl.record(pkey, for_update=True).output('dict')
        self.doctbl.delete(record)
        self.db.commit()
        assert self.exampleFiles('trash') is None

    # ------------------------------------------------------------------
    # docbag links rewriting on rename
    # ------------------------------------------------------------------

    def test_rename_updates_links(self):
        processor_name = self.doctbl.pkg.htmlProcessorName()
        target_id = self.addDoc('link_target_v1')
        docbag = Bag()
        docbag['en.title'] = 'Linking page'
        docbag['en.rst'] = '`See also <%s/link_target_v1>`_' % processor_name
        linking_id = self.addDoc('linking_page', docbag=docbag)
        self.updateDoc(target_id, name='link_target_v2')
        updated_docbag = Bag(self.doctbl.record(linking_id).output('dict')['docbag'])
        assert '<%s/link_target_v2>' % processor_name in updated_docbag['en.rst']
        assert 'link_target_v1' not in updated_docbag['en.rst']

    # ------------------------------------------------------------------
    # bulk regeneration (the contract used by the export_to_sphinx batch)
    # ------------------------------------------------------------------

    def test_regenerate_after_site_loss(self):
        pkey = self.addDoc('survivor', sourcebag=sourceBag(('v000', "print('keep')")))
        self.app.site.storageNode('site:webpages').delete()
        assert self.exampleFiles('survivor') is None
        record = self.doctbl.record(pkey).output('dict')
        self.doctbl.writeModulesFromSourceBag(dict(
            hierarchical_name=record['hierarchical_name'],
            sourcebag=Bag(record['sourcebag'])))
        assert self.exampleFiles('survivor') == ['v000.py']
        assert self.exampleSource('survivor', 'v000.py') == "print('keep')"
