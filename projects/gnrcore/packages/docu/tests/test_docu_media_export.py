"""Tests for the public-url media linking of the docu package.

Exercise the attachment links of docu.documentation.atcAsRstTable and the
image rewriting of the export_to_sphinx batch against a real database
(gnrdevelop instance) and real local storage services backed by temporary
directories: media already living on a storage service is linked by the
stable public_url of its own node (unsigned on signing services, plain
instance-served elsewhere), anything else falls back to the standard
fileurl / download-and-embed behavior.
"""
import os
import re
import shutil
import tempfile
from datetime import date
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.lib.services.storage import BaseLocalService, StorageNode

from core.common import BaseGnrAppTest

MEDIA_HOST = 'https://media.example.org'
INSTANCE_HOST = 'https://instance.example.org'
IMAGEFINDER = re.compile(r"\.\. image:: ([\w./:-]+)")


class SigningLocalService(BaseLocalService):
    """Local service mimicking a signing storage (e.g. aws_s3): url() is signed
    and expiring while public_url() stays plain and permanent."""

    def url(self, *args, **kwargs):
        return '%s?Signature=deadbeef&Expires=123' % super().url(*args, **kwargs)

    def public_url(self, *args, **kwargs):
        return super().url(*args, **kwargs)


class StorageSiteStub:
    """Minimal site wiring exposing real local storage services to the model."""

    def __init__(self, gnrapp, mainpackage, services_dirs):
        self.gnrapp = gnrapp
        self.mainpackage = mainpackage
        self.external_host = MEDIA_HOST
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

    def externalUrl(self, url, **kwargs):
        return '%s%s' % (INSTANCE_HOST, url)

    def pathListFromUrl(self, url):
        return list(filter(None, urlsplit(url).path.split('/')))

    def storageType(self, path_list):
        if path_list[0].startswith('_storage'):
            return 'storage'

    def storageNodeFromPathList(self, path_list, storageType=None):
        service_name, path = path_list[1], '/'.join(path_list[2:])
        if service_name not in self.services:
            return None
        return self.storageNode('%s:%s' % (service_name, path))


class TestDocuMediaExport(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.doctbl = cls.db.table('docu.documentation')
        cls.atctbl = cls.db.table('docu.documentation_atc')
        cls.media_dir = tempfile.mkdtemp(prefix='gnr_docu_media_')
        cls.attachments_dir = tempfile.mkdtemp(prefix='gnr_docu_atc_')
        cls.app.site = StorageSiteStub(cls.app, 'docu', {
            'testmedia': cls.media_dir,
            'documentation': cls.attachments_dir,
        })
        cls.signed_dir = tempfile.mkdtemp(prefix='gnr_docu_signed_')
        signed_service = SigningLocalService(parent=cls.app.site, base_path=cls.signed_dir)
        signed_service.service_name = 'signedmedia'
        cls.app.site.services['signedmedia'] = signed_service
        cls._makeFixture()

    @classmethod
    def teardown_class(cls):
        for folder in (cls.media_dir, cls.attachments_dir, cls.signed_dir):
            shutil.rmtree(folder, ignore_errors=True)
        super().teardown_class()

    @classmethod
    def _addDoc(cls, name):
        record = dict(name=name, publish_date=date.today())
        cls.doctbl.insert(record)
        return record['id']

    @classmethod
    def _addAttachment(cls, maintable_id, description, filepath=None,
                       content=None, external_url=None):
        if content is not None:
            with cls.app.site.storageNode(filepath).open('wb') as attachment_file:
                attachment_file.write(content)
        cls.atctbl.insert(dict(maintable_id=maintable_id, description=description,
                               filepath=filepath, external_url=external_url,
                               atc_download=True))

    @classmethod
    def _makeFixture(cls):
        cls.doc_id = cls._addDoc('mediapage')
        cls._addAttachment(cls.doc_id, 'User manual',
                           filepath='documentation:attachments/manual.pdf',
                           content=b'%PDF-fake-manual')
        cls.signed_doc_id = cls._addDoc('signedatc')
        cls._addAttachment(cls.signed_doc_id, 'Signed manual',
                           filepath='signedmedia:attachments/signed.pdf',
                           content=b'%PDF-signed-manual')
        cls.missing_doc_id = cls._addDoc('missingatc')
        cls._addAttachment(cls.missing_doc_id, 'Lost file',
                           filepath='documentation:attachments/lost.pdf')
        cls.foreign_doc_id = cls._addDoc('foreignatc')
        cls._addAttachment(cls.foreign_doc_id, 'Foreign doc',
                           external_url='https://elsewhere.example.org/doc.pdf')
        cls.db.commit()

    def storageUrl(self, service, path):
        return '%s/_storage/%s/%s' % (MEDIA_HOST, service, path)

    # ------------------------------------------------------------------
    # atcAsRstTable: attachments linked by the public url of their node
    # ------------------------------------------------------------------

    def _fileurl(self, doc_id):
        atc = self.atctbl.query(columns='*,$fileurl', where='$maintable_id=:pkey',
                                pkey=doc_id).fetch()[0]
        return atc['fileurl']

    def test_atc_public_url(self):
        rst = self.doctbl.atcAsRstTable(self.doc_id, host=INSTANCE_HOST)
        expected = self.storageUrl('documentation', 'attachments/manual.pdf')
        assert '`User manual <%s>`_' % expected in rst
        assert 'download=1' not in rst

    def test_atc_signing_storage(self):
        rst = self.doctbl.atcAsRstTable(self.signed_doc_id, host=INSTANCE_HOST)
        node = self.app.site.storageNode('signedmedia:attachments/signed.pdf')
        assert 'Signature' in node.url()
        assert '`Signed manual <%s>`_' % node.public_url() in rst
        assert 'Signature' not in rst

    def test_atc_missing_file_fallback(self):
        rst = self.doctbl.atcAsRstTable(self.missing_doc_id, host=INSTANCE_HOST)
        expected = '%s%s?download=1' % (INSTANCE_HOST, self._fileurl(self.missing_doc_id))
        assert '`Lost file <%s>`_' % expected in rst

    def test_atc_foreign_document(self):
        rst = self.doctbl.atcAsRstTable(self.foreign_doc_id, host=INSTANCE_HOST)
        assert '`Foreign doc <https://elsewhere.example.org/doc.pdf>`_' in rst

    # ------------------------------------------------------------------
    # export_to_sphinx.fixImages: rst rewriting
    # ------------------------------------------------------------------

    def _batch(self):
        pytest.importorskip('sphinx')
        pytest.importorskip('boto3')
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'resources', 'tables', 'handbook', 'action',
                                   'export_to_sphinx.py')
        module = gnrImport(module_path, avoidDup=True)
        page = SimpleNamespace(db=self.db, btc=None, site=self.app.site,
                               external_host=INSTANCE_HOST,
                               getUuid=lambda: 'test-batch')
        batch = module.Main(page=page, resource_table=self.db.table('docu.handbook'))
        batch.doctable = self.doctbl
        batch.mediaUrlsDict = {}
        batch.imagesDict = {}
        batch.imagesPath = '_static/images'
        batch.curr_pathlist = ['guide']
        return batch

    def _storeImage(self, fullpath, content=b'png-bytes'):
        with self.app.site.storageNode(fullpath).open('wb') as image_file:
            image_file.write(content)

    def test_fiximages_storage_public_url(self):
        self._storeImage('testmedia:pics/logo.png')
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/testmedia/pics/logo.png')
        assert rst == '.. image:: %s' % self.storageUrl('testmedia', 'pics/logo.png')
        assert batch.imagesDict == {}

    def test_fiximages_signing_storage(self):
        self._storeImage('signedmedia:pics/signed.png')
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/signedmedia/pics/signed.png')
        node = self.app.site.storageNode('signedmedia:pics/signed.png')
        assert rst == '.. image:: %s' % node.public_url()
        assert 'Signature' not in rst

    def test_fiximages_uses_cache(self):
        self._storeImage('testmedia:pics/cached.png')
        batch = self._batch()
        ref = '.. image:: /_storage/testmedia/pics/cached.png'
        IMAGEFINDER.sub(batch.fixImages, ref)
        expected = self.storageUrl('testmedia', 'pics/cached.png')
        assert batch.mediaUrlsDict['/_storage/testmedia/pics/cached.png'] == expected
        # remove the stored file: the second occurrence must be served from the cache
        self.app.site.storageNode('testmedia:pics/cached.png').delete()
        rst = IMAGEFINDER.sub(batch.fixImages, ref)
        assert rst == '.. image:: %s' % expected

    def test_fiximages_missing_node_fallback(self):
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/testmedia/pics/nowhere.png')
        assert rst == '.. image:: /_static/images/guide/nowhere.png'
        assert batch.imagesDict == {
            '_static/images/guide/nowhere.png': '/_storage/testmedia/pics/nowhere.png'}

    def test_fiximages_external_url_fallback(self):
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: https://elsewhere.example.org/pic.png')
        assert rst == '.. image:: /_static/images/guide/pic.png'
        assert batch.imagesDict == {
            '_static/images/guide/pic.png': 'https://elsewhere.example.org/pic.png'}

    def test_fiximages_non_storage_path_fallback(self):
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages, '.. image:: /sitemedia/pic.png')
        assert rst == '.. image:: /_static/images/guide/pic.png'
        assert batch.imagesDict == {'_static/images/guide/pic.png': '/sitemedia/pic.png'}
