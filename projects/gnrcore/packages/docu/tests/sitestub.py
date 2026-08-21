"""Minimal site wiring shared by the docu tests.

The package tests run against a real database but without a site, while the docu
model and the export batch reach storage services through it. StorageSiteStub
exposes real local storage services backed by temporary directories, so a test
can exercise the paths the code builds and the files it writes.
"""
from types import SimpleNamespace
from urllib.parse import urlsplit

from gnr.lib.services.storage import BaseLocalService, StorageNode

MEDIA_HOST = 'https://media.example.org'
INSTANCE_HOST = 'https://instance.example.org'


class StorageSiteStub:
    """Site exposing local storage services, one per name/directory pair"""

    def __init__(self, gnrapp=None, mainpackage=None, services_dirs=None):
        self.gnrapp = gnrapp
        self.mainpackage = mainpackage
        self.external_host = MEDIA_HOST
        self.currentPage = SimpleNamespace(isMobile=False, user=None)
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
