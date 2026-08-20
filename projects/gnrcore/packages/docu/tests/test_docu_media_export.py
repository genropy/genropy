"""Tests for the public-url media linking of the docu package.

Exercise the attachment links of docu.documentation.atcAsRstTable and the
image rewriting of the export_to_sphinx batch against a real database
(gnrdevelop instance) and real local storage services backed by temporary
directories. Both go through the same gate, documentation.publicMediaUrl: media
is linked by the stable public_url of its own node only when its storage service
declares a public base, the configuration that states the file is readable by
anyone without the instance. Everything else keeps the previous behavior, so
attachments stay instance-served downloads and images stay embedded in the
build, and the published handbook stays self-contained.
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
PUBLIC_HOST = 'https://cdn.example.org'
BUCKET_HOST = 'https://s3.eu-south-1.amazonaws.com'
IMAGEFINDER = re.compile(r"\.\. image:: ([\w./:-]+)")


class SigningLocalService(BaseLocalService):
    """Local service mimicking a signing storage with a public base of its own
    (e.g. aws_s3 with public_base_url): url() is signed, expiring and served by
    the instance, while public_url() is plain, permanent and served by the
    public base, which declares the content readable by anyone."""

    public_base_url = PUBLIC_HOST

    def url(self, *args, **kwargs):
        return '%s?Signature=deadbeef&Expires=123' % super().url(*args, **kwargs)

    def public_url(self, *args, **kwargs):
        return '/'.join([self.public_base_url, self.service_name] + list(args))


class PrivateBucketLocalService(BaseLocalService):
    """Local service mimicking a signing storage with no public base configured
    (e.g. aws_s3 without public_base_url): public_url() still answers a url on
    the bucket endpoint, outside the instance, but nothing says that bucket is
    publicly readable, so linking it would publish 403s."""

    def url(self, *args, **kwargs):
        return '%s?Signature=deadbeef&Expires=123' % super().url(*args, **kwargs)

    def public_url(self, *args, **kwargs):
        return '/'.join([BUCKET_HOST, self.service_name] + list(args))


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
        cls.bucket_dir = tempfile.mkdtemp(prefix='gnr_docu_bucket_')
        for service_name, service_class, base_path in (
                ('signedmedia', SigningLocalService, cls.signed_dir),
                ('bucketmedia', PrivateBucketLocalService, cls.bucket_dir)):
            service = service_class(parent=cls.app.site, base_path=base_path)
            service.service_name = service_name
            cls.app.site.services[service_name] = service
        cls._makeFixture()

    @classmethod
    def teardown_class(cls):
        for folder in (cls.media_dir, cls.attachments_dir, cls.signed_dir,
                       cls.bucket_dir):
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
        cls.bucket_doc_id = cls._addDoc('bucketatc')
        cls._addAttachment(cls.bucket_doc_id, 'Bucket manual',
                           filepath='bucketmedia:attachments/bucket.pdf',
                           content=b'%PDF-bucket-manual')
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

    def test_atc_instance_storage_keeps_download_link(self):
        """An attachment served by the instance itself keeps the instance link,
        download parameter included: its storage service does not declare it
        publicly readable."""
        rst = self.doctbl.atcAsRstTable(self.doc_id, host=INSTANCE_HOST)
        expected = '%s%s?download=1' % (INSTANCE_HOST, self._fileurl(self.doc_id))
        assert '`User manual <%s>`_' % expected in rst

    def test_atc_public_base_url(self):
        """An attachment whose service declares a public base is linked by its
        unsigned, permanent public url."""
        rst = self.doctbl.atcAsRstTable(self.signed_doc_id, host=INSTANCE_HOST)
        node = self.app.site.storageNode('signedmedia:attachments/signed.pdf')
        assert 'Signature' in node.url()
        assert '`Signed manual <%s>`_' % node.public_url() in rst
        assert 'Signature' not in rst

    def test_atc_private_bucket_keeps_download_link(self):
        """A service answering public_url() with a bucket url it was never told
        is public keeps the instance-served link: publishing that url would mean
        publishing a 403 on a private bucket."""
        rst = self.doctbl.atcAsRstTable(self.bucket_doc_id, host=INSTANCE_HOST)
        expected = '%s%s?download=1' % (INSTANCE_HOST,
                                        self._fileurl(self.bucket_doc_id))
        assert '`Bucket manual <%s>`_' % expected in rst
        assert BUCKET_HOST not in rst

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

    def test_fiximages_instance_storage_embedded(self):
        """An image served by the instance itself keeps being embedded in the
        build: linking it would make the published handbook depend on the
        instance being reachable."""
        self._storeImage('testmedia:pics/logo.png')
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/testmedia/pics/logo.png')
        assert rst == '.. image:: /_static/images/guide/logo.png'
        assert batch.imagesDict == {
            '_static/images/guide/logo.png': '/_storage/testmedia/pics/logo.png'}

    def test_fiximages_public_host_storage_linked(self):
        """An image whose service has a public host of its own is linked by its
        stable public url instead of being embedded."""
        self._storeImage('signedmedia:pics/signed.png')
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/signedmedia/pics/signed.png')
        node = self.app.site.storageNode('signedmedia:pics/signed.png')
        assert rst == '.. image:: %s' % node.public_url()
        assert 'Signature' not in rst
        assert batch.imagesDict == {}

    def test_fiximages_private_bucket_embedded(self):
        """An image on a service with no public base configured is embedded: the
        bucket url public_url() answers is not declared publicly readable."""
        self._storeImage('bucketmedia:pics/bucket.png')
        batch = self._batch()
        rst = IMAGEFINDER.sub(batch.fixImages,
                              '.. image:: /_storage/bucketmedia/pics/bucket.png')
        assert rst == '.. image:: /_static/images/guide/bucket.png'
        assert batch.imagesDict == {
            '_static/images/guide/bucket.png': '/_storage/bucketmedia/pics/bucket.png'}

    def test_publicmediaurl_requires_a_public_base(self):
        """The single gate both halves go through: only a service declaring a
        public base answers a linkable url."""
        self._storeImage('testmedia:pics/served.png')
        self._storeImage('signedmedia:pics/served.png')
        self._storeImage('bucketmedia:pics/served.png')
        instance_node = self.app.site.storageNode('testmedia:pics/served.png')
        public_node = self.app.site.storageNode('signedmedia:pics/served.png')
        bucket_node = self.app.site.storageNode('bucketmedia:pics/served.png')
        assert self.doctbl.publicMediaUrl(instance_node) is None
        assert self.doctbl.publicMediaUrl(bucket_node) is None
        assert self.doctbl.publicMediaUrl(public_node) == public_node.public_url()

    def test_fiximages_uses_cache(self):
        self._storeImage('signedmedia:pics/cached.png')
        batch = self._batch()
        ref = '.. image:: /_storage/signedmedia/pics/cached.png'
        IMAGEFINDER.sub(batch.fixImages, ref)
        expected = self.app.site.storageNode('signedmedia:pics/cached.png').public_url()
        assert batch.mediaUrlsDict['/_storage/signedmedia/pics/cached.png'] == expected
        # remove the stored file: the second occurrence must be served from the cache
        self.app.site.storageNode('signedmedia:pics/cached.png').delete()
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
