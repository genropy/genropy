"""Minimal site wiring shared by the docu tests.

The package tests run against a real database but without a site, while the docu
model and the export batch reach storage services through it. StorageSiteStub
exposes real local storage services backed by temporary directories, so a test
can exercise the paths the code builds and the files it writes, and PageStub
answers the handful of things the model asks the current page for.
"""
from urllib.parse import urlsplit

from gnr.core.gnrbag import Bag
from gnr.lib.services.storage import BaseLocalService, StorageNode

MEDIA_HOST = 'https://media.example.org'
INSTANCE_HOST = 'https://instance.example.org'
PUBLIC_HOST = 'https://cdn.example.org'
BUCKET_HOST = 'https://s3.eu-south-1.amazonaws.com'


class PageStoreStub:
    """In-memory stand-in for the page store, usable as a context manager or
    read straight away, the two ways the framework reaches for it."""

    def __init__(self):
        self.data = Bag()

    def getItem(self, path, default=None):
        value = self.data.getItem(path)
        return default if value is None else value

    def setItem(self, path, value, **kwargs):
        self.data.setItem(path, value, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, value, traceback):
        return False


class PageStub:
    """The page the model and the batches reach for.

    Hierarchical resolvers ask the current page for the connection, a uuid and
    the store they cache their condition in; a batch asks its page for the same
    connection, the site and the external host. One object answers both roles.
    """

    isMobile = False
    user = None
    page_id = 'test-page'
    external_host = INSTANCE_HOST

    def __init__(self, db=None, site=None, btc=None):
        self.db = db
        self.site = site
        self.btc = btc
        self._store = PageStoreStub()
        self._uuid_count = 0

    def getUuid(self):
        self._uuid_count += 1
        return 'test-uuid-%i' % self._uuid_count

    def pageStore(self):
        return self._store


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
    """Site exposing local storage services, one per name/directory pair"""

    def __init__(self, gnrapp=None, mainpackage=None, services_dirs=None):
        self.gnrapp = gnrapp
        self.mainpackage = mainpackage
        self.external_host = MEDIA_HOST
        self.currentPage = PageStub(db=getattr(gnrapp, 'db', None), site=self)
        self.services = {}
        for name, base_path in (services_dirs or {}).items():
            self.addService(name, base_path)

    def addService(self, name, base_path, service_class=None):
        service = (service_class or BaseLocalService)(parent=self, base_path=base_path)
        service.service_name = name
        self.services[name] = service
        return service

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
