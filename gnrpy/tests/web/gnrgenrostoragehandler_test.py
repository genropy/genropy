"""GenroStorageHandler on a real site: which mounts it takes over, which it
leaves to the legacy handler, and that the switch is off by default.

The site is instantiated directly rather than through BaseGnrDaemonTest: these
tests need the storage registry and the resource resolution of a real site, not
a running daemon. If the site cannot be built the whole module skips with the
reason.

Run:
    cd gnrpy && pytest tests/web/gnrgenrostoragehandler_test.py -q
"""

import os
import tempfile

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.lib.services.storage import StorageNode
from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import (GenroStorageHandler,
                                                         LegacyStorageHandler)

pytest.importorskip(
    'genro_storage', reason="genro-storage is an optional dependency (genro_storage extra)")

from gnr.lib.services import storage_genro  # noqa: E402

SITE_NAME = 'gnrdevelop'
SYMBOLIC_MOUNTS = ['rsrc', 'pkg', 'page', 'conn', 'user', 'temp', 'dojo', 'gnr', 'pages']


@pytest.fixture(scope='module')
def site():
    try:
        return gws.GnrWsgiSite(SITE_NAME, site_name=SITE_NAME)
    except Exception as exc:
        pytest.skip("site %r is not available: %s" % (SITE_NAME, exc))


@pytest.fixture(scope='module')
def legacy_handler(site):
    return LegacyStorageHandler(site)


@pytest.fixture
def handler(site, tmp_path):
    """A GenroStorageHandler with an extra local mount of its own."""
    handler = GenroStorageHandler(site)
    handler._setStorageParams('tmpnode', parameters={'base_path': str(tmp_path)},
                              implementation='local')
    handler._configureMounts()
    return handler


class TestSwitch:

    def test_flag_absent_yields_the_legacy_handler(self, site):
        assert site.config['storage?use_genro_storage'] in (None, '', False)
        assert isinstance(site.storage_handler, LegacyStorageHandler)
        assert not isinstance(site.storage_handler, GenroStorageHandler)

    def test_flag_on_yields_the_genro_handler(self, site):
        proxy = site.domains[site.currentDomain]
        previous_handler = proxy._storage_handler
        previous_node = site.config.getNode('storage')
        site.config.setItem('storage', None, use_genro_storage=True)
        proxy._storage_handler = None
        try:
            assert isinstance(site.storage_handler, GenroStorageHandler)
        finally:
            site.config.pop('storage')
            if previous_node is not None:
                site.config.setItem('storage', previous_node.value, **(previous_node.attr or {}))
            proxy._storage_handler = previous_handler


class TestMountRouting:

    def test_local_mounts_are_taken_over(self, handler):
        assert handler.manager.has_mount('tmpnode')
        assert isinstance(handler.storage('tmpnode'), storage_genro.Service)

    def test_raw_mount_is_taken_over_as_a_root_local_mount(self, handler):
        assert handler.manager.has_mount('_raw_')
        service = handler.storage('_raw_')
        assert isinstance(service, storage_genro.Service)
        assert service.mount_config['base_path'] == '/'

    @pytest.mark.parametrize('mount_name', SYMBOLIC_MOUNTS)
    def test_symbolic_mounts_stay_on_the_legacy_service(self, handler, mount_name):
        service = handler.storage(mount_name)
        assert not isinstance(service, storage_genro.Service)
        assert service.service_implementation == 'symbolic'
        assert handler.manager.has_mount(mount_name) is False

    def test_http_mount_stays_on_the_legacy_service(self, handler):
        service = handler.storage('_http_')
        assert not isinstance(service, storage_genro.Service)
        assert service.service_implementation == 'http'

    def test_symbolic_paths_resolve_exactly_as_on_the_legacy_handler(self, handler, legacy_handler):
        """The point of the hybrid: with the switch on, a symbolic node still
        resolves to the very same place."""
        for path in ('rsrc:sys', 'pkg:sys', 'temp:probe.txt', 'gnr:11/js'):
            assert (handler.storageNode(path).internal_path
                    == legacy_handler.storageNode(path).internal_path)

    def test_page_mount_keeps_its_request_scoped_shape(self, handler, legacy_handler):
        """page: is resolved from the current page, which no storage library can
        know; the legacy service must keep owning it."""
        assert (handler.storage('page').service_implementation
                == legacy_handler.storage('page').service_implementation)

    def test_unknown_mount_falls_back_to_the_legacy_local_service(self, handler):
        service = handler.storage('a-name-nobody-configured')
        assert not isinstance(service, storage_genro.Service)

    def test_storage_with_kwargs_stays_on_the_legacy_service(self, handler, tmp_path):
        service = handler.storage('tmpnode', base_path=str(tmp_path))
        assert not isinstance(service, storage_genro.Service)

    def test_readonly_mount_stays_on_the_legacy_service(self, site, tmp_path):
        handler = GenroStorageHandler(site)
        handler._setStorageParams('ro', parameters={'bucket': 'b', 'readonly': 'True'},
                                  implementation='aws_s3')
        handler._configureMounts()
        assert handler.manager.has_mount('ro') is False

    def test_local_mount_on_a_missing_base_path_stays_on_the_legacy_service(self, site, tmp_path):
        handler = GenroStorageHandler(site)
        missing = str(tmp_path / 'not-created-yet')
        handler._setStorageParams('ghost', parameters={'base_path': missing},
                                  implementation='local')
        handler._configureMounts()
        assert handler.manager.has_mount('ghost') is False
        assert not isinstance(handler.storage('ghost'), storage_genro.Service)

    def test_s3_mount_without_bucket_stays_on_the_legacy_service(self, site):
        handler = GenroStorageHandler(site)
        handler._setStorageParams('nobucket', parameters={}, implementation='aws_s3')
        handler._configureMounts()
        assert handler.manager.has_mount('nobucket') is False


class TestRegistrySync:

    def test_update_drops_a_mount_that_stopped_being_mappable(self, handler):
        assert handler.manager.has_mount('tmpnode')
        handler.storage_params['tmpnode'] = {'implementation': 'symbolic'}
        handler._dropMount('tmpnode')
        handler._configureMounts()
        assert handler.manager.has_mount('tmpnode') is False

    def test_remove_from_cache_drops_the_mount(self, handler):
        assert handler.manager.has_mount('tmpnode')
        handler.removeStorageFromCache('tmpnode')
        assert handler.manager.has_mount('tmpnode') is False
        assert 'tmpnode' not in handler.storage_params

    def test_the_two_handlers_share_one_registry(self, site):
        handler = GenroStorageHandler(site)
        legacy = LegacyStorageHandler(site, storage_params=handler.storage_params)
        assert legacy.storage_params is handler.storage_params


class TestNodesOnATakenOverMount:

    def test_the_node_is_a_legacy_storage_node(self, handler):
        node = handler.storageNode('tmpnode:probe.txt')
        assert isinstance(node, StorageNode)
        assert isinstance(node.service, storage_genro.Service)
        assert node.parent is handler.site

    def test_read_write_roundtrip(self, handler):
        node = handler.storageNode('tmpnode:sub/probe.txt')
        with node.open('wb') as fp:
            fp.write(b'through the handler')
        assert node.exists is True
        with node.open('rb') as fp:
            assert fp.read() == b'through the handler'

    def test_node_kwargs_reach_the_node(self, handler):
        node = handler.storageNode('tmpnode:probe.txt', mode='wb', autocreate=-1,
                                   version='_latest_')
        assert node.mode == 'wb'
        assert node.autocreate == -1
        assert node.version == '_latest_'

    def test_copy_to_a_legacy_symbolic_mount(self, handler):
        """A copy that crosses the two worlds: StorageService bridges it by
        content, because the two services report different locations."""
        source = handler.storageNode('tmpnode:crossworld.txt')
        with source.open('wb') as fp:
            fp.write(b'crossing over')
        dest = handler.storageNode('temp:gnr_crossworld_probe.txt')
        try:
            source.copy(dest)
            assert dest.exists is True
            with dest.open('rb') as fp:
                assert fp.read() == b'crossing over'
        finally:
            if dest.exists:
                dest.delete()

    def test_copy_from_a_legacy_local_mount(self, handler):
        """The other direction, between two mounts that are both on the local
        filesystem: it stays a filesystem copy."""
        legacy_dir = tempfile.mkdtemp(prefix='gnr_legacy_local_')
        source_path = os.path.join(legacy_dir, 'legacy.txt')
        with open(source_path, 'wb') as fp:
            fp.write(b'from the legacy side')
        handler._setStorageParams('legacyonly', parameters={'base_path': legacy_dir},
                                  implementation='local')
        legacy_service = handler.storage('legacyonly', base_path=legacy_dir)
        source = StorageNode(parent=handler.site, service=legacy_service, path='legacy.txt')
        dest = handler.storageNode('tmpnode:fromlegacy.txt')
        source.copy(dest)
        assert dest.exists is True
        with dest.open('rb') as fp:
            assert fp.read() == b'from the legacy side'
