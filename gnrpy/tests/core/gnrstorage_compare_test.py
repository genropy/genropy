"""Storage parity: the same test body run against the legacy services and
against genro-storage.

Every test asks the storage under test for a result and compares it with the
contract the legacy services already honour, so what is pinned is "same input,
same observable result in both modes". Where the two legitimately differ, the
difference is asserted explicitly and named, never smoothed over.

Real services on a real filesystem, and on a real S3 endpoint when one is
configured. No daemon and no database: the site is stood in for by SiteStub,
which carries only what StorageNode and the services dereference - the storage
operations themselves are never mocked.

Run:
    cd gnrpy && pytest tests/core/gnrstorage_compare_test.py -q

The S3 half needs an S3-compatible endpoint (MinIO is enough):
    export GNR_TEST_S3_ENDPOINT=http://127.0.0.1:9000
    export GNR_TEST_S3_ACCESS_KEY=minioadmin
    export GNR_TEST_S3_SECRET_KEY=minioadmin
    export GNR_TEST_S3_BUCKET=sandbox
Without GNR_TEST_S3_ENDPOINT, or with an endpoint that does not answer, the S3
tests skip with the reason naming it.
"""

import base64
import hashlib
import importlib.util
import os
import urllib.error
import urllib.request
import uuid

import pytest

from gnr.core.gnrbag import Bag
from gnr.lib.services.storage import (BaseLocalService, NotExistingStorageNode,
                                      StorageNode)

genro_storage = pytest.importorskip(
    'genro_storage', reason="genro-storage is an optional dependency (genro_storage extra)")
from genro_storage import StorageManager  # noqa: E402

from gnr.lib.services import storage_genro  # noqa: E402

MODES = ['legacy', 'genro']

S3_ENDPOINT = os.environ.get('GNR_TEST_S3_ENDPOINT')
S3_ACCESS_KEY = os.environ.get('GNR_TEST_S3_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.environ.get('GNR_TEST_S3_SECRET_KEY', 'minioadmin')
S3_BUCKET = os.environ.get('GNR_TEST_S3_BUCKET', 'sandbox')
S3_PREFIX = os.environ.get('GNR_TEST_S3_PREFIX', 'gnrtest')

CONTENT = b'genropy storage parity payload'


def _s3_unavailable_reason():
    if not S3_ENDPOINT:
        return ("GNR_TEST_S3_ENDPOINT is not set: no S3-compatible endpoint to "
                "compare against (see the module docstring)")
    health = '%s/minio/health/live' % S3_ENDPOINT.rstrip('/')
    try:
        with urllib.request.urlopen(health, timeout=3) as response:
            if response.code != 200:
                return "%s answered %s" % (health, response.code)
    except (urllib.error.URLError, OSError) as exc:
        return "%s is not answering: %s" % (S3_ENDPOINT, exc)
    return None


S3_SKIP_REASON = _s3_unavailable_reason()
requires_s3 = pytest.mark.skipif(S3_SKIP_REASON is not None, reason=str(S3_SKIP_REASON))


def _load_aws_s3_service():
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

    def node(self, path, **kwargs):
        return self.site.storageNode(path, **kwargs)

    def write(self, path, content=CONTENT):
        node = self.node(path)
        with node.open('wb') as fp:
            fp.write(content)
        return node


def _local_storage(mode, base_paths):
    """A Storage with one mount per name in base_paths, all local."""
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


@pytest.fixture(params=MODES)
def local(request, tmp_path):
    """A 'st' mount and a second 'st2' mount, both local, in both modes."""
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    first.mkdir()
    second.mkdir()
    return _local_storage(request.param, {'st': str(first), 'st2': str(second)})


def _s3_storage(mode):
    """A Storage with a 'st' mount on the configured S3 endpoint, under a
    prefix of its own so the two modes never share objects."""
    site = SiteStub()
    prefix = '%s/%s' % (S3_PREFIX, uuid.uuid4().hex[:12])
    if mode == 'legacy':
        legacy_service = _load_aws_s3_service()
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


@pytest.fixture(params=MODES)
def s3(request):
    storage = _s3_storage(request.param)
    yield storage
    root = storage.node('st:')
    if root.exists:
        root.delete()


class StorageParity:
    """The parity body. Subclasses bind `storage` to a local or an S3 mount."""

    @pytest.fixture
    def storage(self):
        raise NotImplementedError

    # ---- existence and kind

    def test_exists_on_missing(self, storage):
        assert storage.node('st:nope.txt').exists is False

    def test_exists_isfile_isdir_on_file(self, storage):
        node = storage.write('st:sub/dir/probe.txt')
        assert node.exists is True
        assert node.isfile is True
        assert node.isdir is False

    def test_exists_isdir_on_directory(self, storage):
        storage.write('st:sub/dir/probe.txt')
        parent = storage.node('st:sub/dir')
        assert parent.exists is True
        assert parent.isdir is True
        assert parent.isfile is False

    # ---- read and write

    def test_open_write_then_read_binary(self, storage):
        node = storage.write('st:bin.dat', b'\x00\x01binary\xff')
        with node.open('rb') as fp:
            assert fp.read() == b'\x00\x01binary\xff'

    def test_open_write_then_read_text(self, storage):
        node = storage.node('st:text.txt')
        with node.open('w') as fp:
            fp.write('a line of text')
        with node.open('r') as fp:
            assert fp.read() == 'a line of text'

    def test_open_write_creates_intermediate_directories(self, storage):
        node = storage.write('st:deep/deeper/deepest/probe.txt')
        assert node.exists is True

    def test_size(self, storage):
        node = storage.write('st:probe.txt')
        assert node.size == len(CONTENT)

    def test_mtime(self, storage):
        node = storage.write('st:probe.txt')
        assert isinstance(node.mtime, float)
        assert node.mtime > 0

    def test_md5hash_is_the_content_md5_when_reported(self, storage):
        node = storage.write('st:probe.txt')
        if node.md5hash is not None:
            assert node.md5hash == hashlib.md5(CONTENT).hexdigest()

    def test_ext_attributes(self, storage):
        node = storage.write('st:probe.txt')
        mtime, size, isdir = node.ext_attributes
        assert size == len(CONTENT)
        assert isdir is False
        assert mtime > 0

    # ---- naming

    def test_fullpath(self, storage):
        assert storage.node('st:sub/probe.txt').fullpath == 'st:sub/probe.txt'

    def test_basename_and_cleanbasename_and_ext(self, storage):
        node = storage.node('st:sub/probe.txt')
        assert node.basename == 'probe.txt'
        assert node.cleanbasename == 'probe'
        assert node.ext == 'txt'

    def test_splitext(self, storage):
        assert storage.node('st:sub/probe.txt').splitext() == ('sub/probe', '.txt')

    def test_internal_path_is_not_empty(self, storage):
        node = storage.node('st:sub/probe.txt')
        assert node.internal_path
        assert node.internal_path.endswith('sub/probe.txt')

    def test_child(self, storage):
        assert storage.node('st:sub').child('probe.txt').fullpath == 'st:sub/probe.txt'

    def test_parent_storage_node(self, storage):
        node = storage.node('st:sub/dir/probe.txt')
        assert node.parentStorageNode.fullpath == 'st:sub/dir'

    # ---- listing

    def test_children(self, storage):
        storage.write('st:listing/a.txt')
        storage.write('st:listing/b.txt')
        names = sorted(child.basename for child in storage.node('st:listing').children())
        assert names == ['a.txt', 'b.txt']

    def test_children_are_storage_nodes(self, storage):
        storage.write('st:listing/a.txt')
        for child in storage.node('st:listing').children():
            assert isinstance(child, StorageNode)
            assert child.exists is True

    def test_children_on_a_file_is_none(self, storage):
        node = storage.write('st:probe.txt')
        assert node.children() is None

    def test_listdir_returns_fullpaths(self, storage):
        storage.write('st:listing/a.txt')
        assert storage.node('st:listing').listdir() == ['st:listing/a.txt']

    # ---- mkdir

    def test_mkdir_then_isdir(self, storage):
        node = storage.node('st:brandnew')
        node.mkdir()
        assert node.isdir is True

    def test_mkdir_on_existing_is_a_noop(self, storage):
        node = storage.node('st:brandnew')
        node.mkdir()
        node.mkdir()
        assert node.isdir is True

    # ---- copy, move, delete

    def test_copy_file(self, storage):
        source = storage.write('st:source.txt')
        dest = source.copy(storage.node('st:copied.txt'))
        assert dest.exists is True
        assert source.exists is True
        with dest.open('rb') as fp:
            assert fp.read() == CONTENT

    def test_copy_into_a_directory_keeps_the_basename(self, storage):
        source = storage.write('st:source.txt')
        target_dir = storage.node('st:target')
        target_dir.mkdir()
        source.copy(target_dir)
        assert storage.node('st:target/source.txt').exists is True

    def test_move_file_rebinds_the_node(self, storage):
        source = storage.write('st:tomove.txt')
        source.move(storage.node('st:moved.txt'))
        assert source.fullpath == 'st:moved.txt'
        assert source.exists is True
        assert storage.node('st:tomove.txt').exists is False

    def test_delete_file(self, storage):
        node = storage.write('st:todelete.txt')
        node.delete()
        assert node.exists is False

    def test_delete_directory(self, storage):
        storage.write('st:tree/a.txt')
        storage.write('st:tree/nested/b.txt')
        tree = storage.node('st:tree')
        tree.delete()
        assert tree.exists is False
        assert storage.node('st:tree/a.txt').exists is False
        assert storage.node('st:tree/nested/b.txt').exists is False

    def test_delete_on_missing_is_a_noop(self, storage):
        storage.node('st:never-existed.txt').delete()

    # ---- base64

    def test_base64_bare(self, storage):
        node = storage.write('st:probe.txt')
        assert node.base64() == base64.b64encode(CONTENT).decode()

    def test_base64_with_autodetected_mime(self, storage):
        node = storage.write('st:probe.txt')
        assert node.base64(mime=True).startswith('data:text/plain;base64,')

    def test_base64_with_explicit_mime(self, storage):
        node = storage.write('st:probe.txt')
        assert node.base64(mime='image/png').startswith('data:image/png;base64,')

    def test_base64_on_missing_is_empty(self, storage):
        assert storage.node('st:nope.txt').base64() == ''

    # ---- urls

    def test_internal_url(self, storage):
        node = storage.write('st:sub/probe.txt')
        assert '/_storage/st/sub/probe.txt' in node.internal_url()

    def test_internal_url_nocache_carries_mtime(self, storage):
        node = storage.write('st:sub/probe.txt')
        assert 'mtime=' in node.internal_url(nocache=True)

    def test_url_is_a_string(self, storage):
        node = storage.write('st:sub/probe.txt')
        assert isinstance(node.url(), str)
        assert node.url()

    # ---- local_path

    def test_local_path_reads_the_content(self, storage):
        node = storage.write('st:probe.txt')
        with node.local_path() as local_path:
            with open(local_path, 'rb') as fp:
                assert fp.read() == CONTENT

    def test_local_path_write_mode_pushes_changes_back(self, storage):
        node = storage.write('st:probe.txt')
        with node.local_path(mode='wb') as local_path:
            with open(local_path, 'wb') as fp:
                fp.write(b'rewritten through local_path')
        with node.open('rb') as fp:
            assert fp.read() == b'rewritten through local_path'

    # ---- node kwargs

    def test_must_exist_raises_on_missing(self, storage):
        with pytest.raises(NotExistingStorageNode):
            storage.node('st:nope.txt', must_exist=True)

    def test_must_exist_passes_on_existing(self, storage):
        storage.write('st:probe.txt')
        assert storage.node('st:probe.txt', must_exist=True).exists is True

    def test_mode_is_kept_on_the_node(self, storage):
        assert storage.node('st:probe.txt', mode='wb').mode == 'wb'

    def test_versions_returns_a_list(self, storage):
        storage.write('st:probe.txt')
        assert isinstance(storage.node('st:probe.txt').versions, list)


class TestLocalParity(StorageParity):
    """The parity body on a local mount."""

    @pytest.fixture
    def storage(self, local):
        return local

    def test_copy_across_mounts(self, local):
        source = local.write('st:source.txt')
        dest = source.copy(local.node('st2:copied.txt'))
        assert dest.exists is True
        with dest.open('rb') as fp:
            assert fp.read() == CONTENT

    def test_move_across_mounts(self, local):
        source = local.write('st:tomove.txt')
        source.move(local.node('st2:moved.txt'))
        assert source.fullpath == 'st2:moved.txt'
        assert source.exists is True
        assert local.node('st:tomove.txt').exists is False

    def test_md5hash_matches_content(self, local):
        node = local.write('st:probe.txt')
        assert node.md5hash == hashlib.md5(CONTENT).hexdigest()

    def test_internal_path_is_the_filesystem_path(self, local):
        node = local.write('st:sub/probe.txt')
        assert os.path.isabs(node.internal_path)
        assert os.path.exists(node.internal_path)

    def test_local_path_is_the_file_itself(self, local):
        node = local.write('st:probe.txt')
        with node.local_path() as local_path:
            assert local_path == node.internal_path


@requires_s3
class TestS3Parity(StorageParity):
    """The parity body on an S3 mount."""

    @pytest.fixture
    def storage(self, s3):
        return s3

    def test_internal_path_is_the_object_key(self, s3):
        node = s3.write('st:sub/probe.txt')
        assert node.internal_path == '%s/sub/probe.txt' % s3.prefix

    def test_internal_url_is_served_as_a_download(self, s3):
        node = s3.write('st:sub/probe.txt')
        assert '_download=True' in node.internal_url()

    def test_url_is_presigned(self, s3):
        node = s3.write('st:sub/probe.txt')
        assert 'X-Amz-Signature' in node.url()

    def test_url_content_is_fetchable(self, s3):
        node = s3.write('st:sub/probe.txt')
        with urllib.request.urlopen(node.url(), timeout=10) as response:
            assert response.read() == CONTENT

    def test_local_path_is_a_temporary_copy(self, s3):
        node = s3.write('st:probe.txt')
        with node.local_path() as local_path:
            assert os.path.exists(local_path)
            assert local_path != node.internal_path


class TestNamedDivergences:
    """Where the two modes legitimately differ, the difference is pinned here
    rather than hidden in the parity body."""

    def test_missing_file_metadata_legacy_local_raises_genro_returns_none(self, tmp_path):
        """On a local mount, the legacy service dereferences a None stat and
        raises AttributeError; the genro-storage service reports None, as the
        legacy aws_s3 service already does."""
        base = tmp_path / 'base'
        base.mkdir()
        legacy = _local_storage('legacy', {'st': str(base)})
        genro = _local_storage('genro', {'st': str(base)})
        with pytest.raises(AttributeError):
            legacy.node('st:nope.txt').mtime
        assert genro.node('st:nope.txt').mtime is None
        assert genro.node('st:nope.txt').size is None
        assert genro.node('st:nope.txt').md5hash is None

    def test_parent_traversal_is_refused_by_genro_storage(self, tmp_path):
        """genro-storage refuses '..' in a path; the legacy service resolves it."""
        base = tmp_path / 'base'
        base.mkdir()
        genro = _local_storage('genro', {'st': str(base)})
        with pytest.raises(ValueError):
            genro.node('st:sub/../escaped.txt').exists

    @requires_s3
    def test_md5hash_on_s3_legacy_gives_up_on_a_multipart_etag(self):
        """The legacy aws_s3 service reports the object ETag as md5, and only
        when it is 32 characters long: a multipart upload (which is what
        smart_open does, and what MinIO reports back) makes it give up and
        return None. genro-storage reports the content md5 either way."""
        legacy = _s3_storage('legacy')
        genro = _s3_storage('genro')
        try:
            legacy_node = legacy.write('st:probe.txt')
            genro_node = genro.write('st:probe.txt')
            assert genro_node.md5hash == hashlib.md5(CONTENT).hexdigest()
            assert legacy_node.md5hash in (None, hashlib.md5(CONTENT).hexdigest())
        finally:
            for storage in (legacy, genro):
                root = storage.node('st:')
                if root.exists:
                    root.delete()

    @requires_s3
    def test_local_path_keep_is_refused_on_a_remote_genro_mount(self):
        """The legacy S3 service can keep the temporary file; genro-storage's
        context manager always removes it, so keep=True is refused loudly
        instead of silently doing nothing."""
        site = SiteStub()
        prefix = '%s/%s' % (S3_PREFIX, uuid.uuid4().hex[:12])
        config = {'name': 'st', 'protocol': 's3', 'bucket': S3_BUCKET,
                  'base_path': prefix, 'access_key': S3_ACCESS_KEY,
                  'secret_key': S3_SECRET_KEY, 'endpoint_url': S3_ENDPOINT}
        manager = StorageManager()
        manager.configure([config])
        site.add('st', storage_genro.Service(
            parent=site, manager=manager, mount_name='st', mount_config=config), 'aws_s3')
        node = site.storageNode('st:probe.txt')
        with node.open('wb') as fp:
            fp.write(CONTENT)
        try:
            with pytest.raises(NotImplementedError):
                node.local_path(keep=True)
        finally:
            node.delete()
