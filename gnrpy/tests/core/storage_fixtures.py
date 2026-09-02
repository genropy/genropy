"""Shared scaffolding for the storage parity tests and the storage benchmark.

Builds the same mount in either mode - through the legacy services or through
genro-storage - so a test body can run twice and be compared. Only the site is
stood in for; the storage services and the storage itself are real.

The S3 half needs an S3-compatible endpoint (MinIO is enough):
    export GNR_TEST_S3_ENDPOINT=http://127.0.0.1:9000
    export GNR_TEST_S3_ACCESS_KEY=minioadmin
    export GNR_TEST_S3_SECRET_KEY=minioadmin
    export GNR_TEST_S3_BUCKET=sandbox
    export GNR_TEST_S3_PREFIX=gnrtest
Without GNR_TEST_S3_ENDPOINT, or with an endpoint that does not answer,
s3_unavailable_reason() explains why and the callers skip.
"""

import importlib.util
import os
import urllib.error
import urllib.request
import uuid

from genro_storage import StorageManager

from gnr.core.gnrbag import Bag
from gnr.lib.services import storage_genro
from gnr.lib.services.storage import BaseLocalService, StorageNode

MODES = ['legacy', 'genro']

S3_ENDPOINT = os.environ.get('GNR_TEST_S3_ENDPOINT')
S3_ACCESS_KEY = os.environ.get('GNR_TEST_S3_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.environ.get('GNR_TEST_S3_SECRET_KEY', 'minioadmin')
S3_BUCKET = os.environ.get('GNR_TEST_S3_BUCKET', 'sandbox')
S3_PREFIX = os.environ.get('GNR_TEST_S3_PREFIX', 'gnrtest')

CONTENT = b'genropy storage parity payload'


def s3_unavailable_reason():
    """Why the S3 half cannot run, or None when it can."""
    if not S3_ENDPOINT:
        return ("GNR_TEST_S3_ENDPOINT is not set: no S3-compatible endpoint to "
                "compare against (see tests/core/storage_fixtures.py)")
    health = '%s/minio/health/live' % S3_ENDPOINT.rstrip('/')
    try:
        with urllib.request.urlopen(health, timeout=3) as response:
            if response.code != 200:
                return "%s answered %s" % (health, response.code)
    except (urllib.error.URLError, OSError) as exc:
        return "%s is not answering: %s" % (S3_ENDPOINT, exc)
    return None


def load_legacy_aws_s3_service():
    """Load the legacy aws_s3 service, which lives as a site resource."""
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(
        here, '..', '..', '..', 'projects', 'gnrcore', 'packages', 'sys',
        'resources', 'services', 'storage', 'aws_s3.py'))
    spec = importlib.util.spec_from_file_location('gnrtest_legacy_aws_s3', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Service


class SiteStub:
    """Minimal stand-in for the site: only what StorageNode and the services
    dereference."""

    external_host = 'http://localhost:8080'
    cache_max_age = None
    _local_mode = False

    def __init__(self):
        self.services = {}
        app_config = Bag()
        app_config['packages'] = Bag()
        self.gnrapp = type('GnrAppStub', (), {'config': app_config})()

    def add(self, service_name, service, implementation=None):
        service.service_name = service_name
        service.service_implementation = implementation
        self.services[service_name] = service
        return service

    def storageNode(self, path, **kwargs):
        service_name, _, storage_path = path.partition(':')
        return StorageNode(parent=self, service=self.services[service_name],
                           path=storage_path, **kwargs)

    def getService(self, service_type=None, service_name=None, **kwargs):
        return self.services[service_name]

    def not_found_exception(self, environ, start_response):
        start_response('404 Not Found', [])
        return [b'']

    def redirect(self, environ, start_response, location=None, temporary=False):
        start_response('302 Found', [('Location', location)])
        return [b'redirected']


class Storage:
    """The storage under test, in one of the two modes."""

    def __init__(self, site, mode, mounts):
        self.site = site
        self.mode = mode
        self.mounts = mounts
        self.prefix = None

    def node(self, path, **kwargs):
        return self.site.storageNode(path, **kwargs)

    def write(self, path, content=CONTENT):
        node = self.node(path)
        with node.open('wb') as fp:
            fp.write(content)
        return node

    def cleanup(self):
        for mount in self.mounts:
            root = self.node('%s:' % mount)
            if root.exists:
                root.delete()


def local_storage(mode, base_paths):
    """A Storage with one local mount per name in base_paths."""
    site = SiteStub()
    manager = StorageManager() if mode == 'genro' else None
    for name, base_path in base_paths.items():
        if mode == 'legacy':
            site.add(name, BaseLocalService(parent=site, base_path=base_path), 'local')
        else:
            config = {'name': name, 'protocol': 'local', 'base_path': base_path}
            manager.configure([config])
            site.add(name, storage_genro.Service(
                parent=site, manager=manager, mount_name=name, mount_config=config), 'local')
    return Storage(site, mode, list(base_paths))


def s3_storage(mode):
    """A Storage with a 'st' mount on the configured S3 endpoint, under a
    prefix of its own so the two modes never share objects."""
    site = SiteStub()
    prefix = '%s/%s' % (S3_PREFIX, uuid.uuid4().hex[:12])
    if mode == 'legacy':
        legacy_service = load_legacy_aws_s3_service()
        site.add('st', legacy_service(
            parent=site, bucket=S3_BUCKET, base_path=prefix,
            aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY,
            region_name='us-east-1', custom_endpoint=True, endpoint_url=S3_ENDPOINT,
            versioned=False), 'aws_s3')
    else:
        config = {'name': 'st', 'protocol': 's3', 'bucket': S3_BUCKET,
                  'base_path': prefix, 'access_key': S3_ACCESS_KEY,
                  'secret_key': S3_SECRET_KEY, 'endpoint_url': S3_ENDPOINT}
        manager = StorageManager()
        manager.configure([config])
        site.add('st', storage_genro.Service(
            parent=site, manager=manager, mount_name='st', mount_config=config,
            versioned=False), 'aws_s3')
    storage = Storage(site, mode, ['st'])
    storage.prefix = prefix
    return storage
