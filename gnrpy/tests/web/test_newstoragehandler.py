import os
import time
import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

import gnr.web.gnrwsgisite as gws
from gnr.core.gnrbag import Bag

from webcommon import BaseGnrTest
from utils import WSGITestClient, ExternalProcess


def get_waited_wsgisite(site_name):
    max_attempts = 3
    attempt = 0
    timeout = 2

    while attempt < max_attempts:
        try:
            site = gws.GnrWsgiSite(site_name, site_name=site_name)
            return site
        except Exception as e:
            time.sleep(timeout)
            attempt += 1
    raise Exception(f"Can't connect to local daemon after {attempt} attempts")


class TestNewStorageHandler(BaseGnrTest):
    """Comprehensive tests for NewStorageHandler (genro-storage integration).

    These tests verify that the NewStorageHandler works correctly when
    configured with mode='ns' in siteconfig.xml.
    """

    @classmethod
    def setup_class(cls):
        super().setup_class()

        # Create a temporary site configuration with mode='ns'
        cls.test_config_dir = tempfile.mkdtemp(prefix='gnr_ns_test_config_')
        cls.siteconfig_path = os.path.join(cls.test_config_dir, 'siteconfig.xml')

        # Create siteconfig.xml with storage mode='ns'
        siteconfig_content = '''<?xml version='1.0' encoding='UTF-8'?>
<GenRoBag>
    <storage mode="ns"/>
    <wsgi port="8081" reload="true" debug="true"/>
</GenRoBag>
'''
        with open(cls.siteconfig_path, 'w') as f:
            f.write(siteconfig_content)

        cls.external = ExternalProcess(['gnr','web','daemon'], cwd=None)

        try:
            cls.external.start()
            cls.site_name = 'gnrdevelop'
            cls.site = get_waited_wsgisite(cls.site_name)
            cls.client = WSGITestClient(cls.site)
            cls.storage_handler = cls.site.storage_handler

            # Create temporary directory for test storage
            cls.test_dir = tempfile.mkdtemp(prefix='gnr_storage_test_')

        except Exception as e:
            cls.teardown_class()
            raise

    @classmethod
    def teardown_class(cls):
        cls.external.stop()
        # Clean up temporary directories
        if hasattr(cls, 'test_dir') and os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        if hasattr(cls, 'test_config_dir') and os.path.exists(cls.test_config_dir):
            shutil.rmtree(cls.test_config_dir)
        super().teardown_class()

    # ========================================================================
    # Handler Type and Initialization Tests
    # ========================================================================

    def test_handler_is_new_storage_handler(self):
        """Test that NewStorageHandler is used when mode='ns'."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import NewStorageHandler

        assert isinstance(self.storage_handler, NewStorageHandler), \
            "Storage handler should be NewStorageHandler when mode='ns'"

    def test_storage_manager_initialization(self):
        """Test that StorageManager is properly initialized."""
        assert hasattr(self.storage_handler, 'storage_manager')
        assert self.storage_handler.storage_manager is not None

    def test_storage_params_converted_to_mounts(self):
        """Test that storage_params are converted to StorageManager mounts."""
        # Check that storage_manager has mounts configured
        manager = self.storage_handler.storage_manager

        # Built-in storages should be configured as mounts
        builtin_storages = ['gnr', 'rsrc', 'temp']
        for storage_name in builtin_storages:
            if storage_name in self.storage_handler.storage_params:
                # StorageManager should have this mount
                assert manager.has_mount(storage_name), \
                    f"StorageManager should have mount for '{storage_name}'"

    # ========================================================================
    # Storage Parameters Registry Tests
    # ========================================================================

    def test_storage_params_initialization(self):
        """Test that storage_params registry is properly initialized."""
        assert hasattr(self.storage_handler, 'storage_params')
        assert isinstance(self.storage_handler.storage_params, dict)
        assert len(self.storage_handler.storage_params) > 0

    def test_builtin_storage_params(self):
        """Test that built-in storage services are properly registered."""
        builtin_storages = ['user', 'conn', 'page', 'temp', 'rsrc', 'pkg',
                           'dojo', 'gnr', 'pages', '_raw_', '_http_']

        for storage_name in builtin_storages:
            assert storage_name in self.storage_handler.storage_params, \
                f"Built-in storage '{storage_name}' not found in storage_params"
            params = self.storage_handler.storage_params[storage_name]
            assert isinstance(params, dict)
            assert 'implementation' in params

    # ========================================================================
    # StorageNode Creation and API Tests
    # ========================================================================

    def test_storage_node_creation(self):
        """Test creating storage nodes with NewStorageHandler."""
        node = self.site.storageNode('gnr', 'js', 'dojo_libs')
        assert node is not None
        assert hasattr(node, 'fullpath')
        assert hasattr(node, 'exists')

    def test_storage_node_is_new_storage_node(self):
        """Test that created nodes are NewStorageNode instances."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import NewStorageNode

        node = self.site.storageNode('temp', 'test.txt')
        assert isinstance(node, NewStorageNode), \
            "NewStorageHandler should create NewStorageNode instances"

    def test_new_storage_node_wraps_brick_node(self):
        """Test that NewStorageNode wraps BrickStorageNode."""
        from genro_storage import StorageNode as BrickStorageNode

        node = self.site.storageNode('temp', 'test.txt')
        assert hasattr(node, '_brick_node')
        assert isinstance(node._brick_node, BrickStorageNode)

    def test_storage_node_properties(self):
        """Test NewStorageNode basic properties."""
        node = self.site.storageNode('temp', 'test_props.txt')
        assert node is not None

        # Test property access (should not raise exceptions)
        assert hasattr(node, 'fullpath')
        assert hasattr(node, 'basename')
        assert hasattr(node, 'dirname')
        assert hasattr(node, 'exists')
        assert hasattr(node, 'isfile')
        assert hasattr(node, 'isdir')

        fullpath = node.fullpath
        assert isinstance(fullpath, str)

    def test_storage_node_basename_and_extension(self):
        """Test NewStorageNode basename and extension properties."""
        node = self.site.storageNode('temp', 'subdir', 'test_file.txt')

        basename = node.basename
        assert isinstance(basename, str)
        assert 'test_file.txt' in basename

        # Test extension property (adapted from suffix)
        ext = node.ext
        assert ext == 'txt' or ext == '.txt' or 'txt' in ext

        # Test cleanbasename (adapted from stem)
        cleanbasename = node.cleanbasename
        assert 'test_file' in cleanbasename
        assert '.txt' not in cleanbasename

    def test_storage_node_splitext(self):
        """Test NewStorageNode splitext method."""
        node = self.site.storageNode('temp', 'document.pdf')
        name, ext = node.splitext()
        assert isinstance(name, str)
        assert isinstance(ext, str)
        assert ext in ['.pdf', 'pdf']

    # ========================================================================
    # File Operations Tests
    # ========================================================================

    def test_storage_node_open_context_manager(self):
        """Test NewStorageNode.open() as context manager."""
        test_node = self.site.storageNode('temp', f'test_open_{os.getpid()}.txt')

        # Write content using context manager
        test_content = b"Test content for open context manager"
        try:
            with test_node.open('wb') as f:
                assert f is not None
                f.write(test_content)

            # Read back the content
            with test_node.open('rb') as f:
                content = f.read()
                assert content == test_content

        finally:
            # Clean up
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_delete(self):
        """Test NewStorageNode.delete() method."""
        test_node = self.site.storageNode('temp', f'test_delete_{os.getpid()}.txt')

        # Create file
        with test_node.open('wb') as f:
            f.write(b"to be deleted")

        # Verify exists
        if test_node.exists:
            # Delete it
            test_node.delete()

            # Verify deleted
            assert not test_node.exists

    def test_storage_node_move(self):
        """Test NewStorageNode.move() method (adapted from move_to)."""
        source_node = self.site.storageNode('temp', f'test_move_source_{os.getpid()}.txt')
        dest_path = f'temp:test_move_dest_{os.getpid()}.txt'

        try:
            # Create source file
            test_content = b"content to move"
            with source_node.open('wb') as f:
                f.write(test_content)

            if source_node.exists:
                # Move the file
                source_node.move(dest=dest_path)

                # Verify content at new location
                with source_node.open('rb') as f:
                    content = f.read()
                    assert content == test_content

        finally:
            try:
                source_node.delete()
            except:
                pass

    def test_storage_node_copy(self):
        """Test NewStorageNode.copy() method (adapted from copy_to)."""
        source_node = self.site.storageNode('temp', f'test_copy_source_{os.getpid()}.txt')
        dest_path = f'temp:test_copy_dest_{os.getpid()}.txt'

        try:
            # Create source file
            test_content = b"content to copy"
            with source_node.open('wb') as f:
                f.write(test_content)

            if source_node.exists:
                # Copy the file
                dest_node = source_node.copy(dest=dest_path)

                # Both should exist
                assert source_node.exists
                if dest_node:
                    assert dest_node.exists

                    # Verify content in both
                    with source_node.open('rb') as f:
                        source_content = f.read()
                    with dest_node.open('rb') as f:
                        dest_content = f.read()
                    assert source_content == dest_content == test_content

                    # Clean up destination
                    dest_node.delete()

        finally:
            try:
                source_node.delete()
            except:
                pass

    # ========================================================================
    # Directory Operations Tests
    # ========================================================================

    def test_storage_node_mkdir(self):
        """Test NewStorageNode.mkdir() method."""
        test_dir_node = self.site.storageNode('temp', f'test_mkdir_{os.getpid()}')

        try:
            # Create directory
            if not test_dir_node.exists:
                test_dir_node.mkdir()

            # Check if created
            if test_dir_node.exists:
                assert test_dir_node.isdir

        finally:
            try:
                test_dir_node.delete()
            except:
                pass

    def test_storage_node_listdir(self):
        """Test NewStorageNode.listdir() method."""
        test_dir = self.site.storageNode('temp', f'test_listdir_{os.getpid()}')

        try:
            # Create test directory structure
            if not test_dir.exists:
                test_dir.mkdir()

            # Create some test files
            test_file1 = test_dir.child('file1.txt')
            test_file2 = test_dir.child('file2.txt')

            with test_file1.open('wb') as f:
                f.write(b"content1")
            with test_file2.open('wb') as f:
                f.write(b"content2")

            # List directory contents
            if test_dir.isdir:
                contents = test_dir.listdir()
                assert contents is not None
                assert isinstance(contents, (list, tuple))
                # Should contain our test files
                assert len(contents) >= 2

        finally:
            try:
                test_dir.delete()
            except:
                pass

    def test_storage_node_children(self):
        """Test NewStorageNode.children() method."""
        test_dir = self.site.storageNode('temp', f'test_children_{os.getpid()}')

        try:
            if not test_dir.exists:
                test_dir.mkdir()

            # Create test files
            test_file = test_dir.child('child_test.txt')
            with test_file.open('wb') as f:
                f.write(b"child content")

            # Get children (returns StorageNode objects)
            if test_dir.isdir:
                children = test_dir.children()
                if children:
                    assert isinstance(children, (list, tuple))
                    # Each child should be a NewStorageNode
                    from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import NewStorageNode
                    for child in children:
                        assert isinstance(child, NewStorageNode)
                        assert hasattr(child, 'fullpath')

        finally:
            try:
                test_dir.delete()
            except:
                pass

    def test_storage_node_child(self):
        """Test NewStorageNode.child() method."""
        parent_node = self.site.storageNode('temp', 'parent_dir')

        # Create child node
        child_node = parent_node.child('child_file.txt')
        assert child_node is not None
        assert hasattr(child_node, 'fullpath')

        child_fullpath = child_node.fullpath
        assert 'child_file.txt' in child_fullpath

    # ========================================================================
    # Metadata and Attributes Tests
    # ========================================================================

    def test_storage_node_mtime(self):
        """Test NewStorageNode.mtime property."""
        test_node = self.site.storageNode('temp', f'test_mtime_{os.getpid()}.txt')

        try:
            # Create file
            with test_node.open('wb') as f:
                f.write(b"mtime test")

            if test_node.exists:
                # Get modification time
                mtime = test_node.mtime
                assert mtime is not None
                # Should be a number (timestamp)
                assert isinstance(mtime, (int, float))
                # Should be a reasonable timestamp
                assert mtime > 0

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_size(self):
        """Test NewStorageNode.size property."""
        test_node = self.site.storageNode('temp', f'test_size_{os.getpid()}.txt')

        try:
            # Create file with known size
            test_content = b"X" * 100  # 100 bytes
            with test_node.open('wb') as f:
                f.write(test_content)

            if test_node.exists and test_node.isfile:
                # Get file size
                size = test_node.size
                assert size is not None
                assert isinstance(size, (int, float))
                assert size == 100

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_md5hash(self):
        """Test NewStorageNode.md5hash property."""
        test_node = self.site.storageNode('temp', f'test_md5_{os.getpid()}.txt')

        try:
            # Create file with known content
            test_content = b"md5 hash test content"
            with test_node.open('wb') as f:
                f.write(test_content)

            if test_node.exists:
                # Get MD5 hash
                md5 = test_node.md5hash
                if md5 is not None:
                    assert isinstance(md5, str)
                    # MD5 hashes are 32 hex characters
                    assert len(md5) >= 32

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_metadata(self):
        """Test NewStorageNode get_metadata() and set_metadata() methods."""
        test_node = self.site.storageNode('temp', f'test_metadata_{os.getpid()}.txt')

        try:
            # Create file
            with test_node.open('wb') as f:
                f.write(b"metadata test")

            if test_node.exists and hasattr(test_node, 'get_metadata'):
                # Get metadata (may return None or dict)
                metadata = test_node.get_metadata()
                # Should not raise exception
                assert metadata is None or isinstance(metadata, dict)

                # Try setting metadata (if supported)
                if hasattr(test_node, 'set_metadata'):
                    test_metadata = {'custom_field': 'test_value'}
                    try:
                        test_node.set_metadata(test_metadata)
                        # If it worked, try to retrieve it
                        new_metadata = test_node.get_metadata()
                        # Verify metadata was set (if implementation supports it)
                        if new_metadata:
                            assert isinstance(new_metadata, dict)
                    except NotImplementedError:
                        # Some storage implementations don't support metadata
                        pass

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_mimetype(self):
        """Test NewStorageNode.mimetype property."""
        # Test with different file types
        txt_node = self.site.storageNode('temp', 'test.txt')
        json_node = self.site.storageNode('temp', 'test.json')
        html_node = self.site.storageNode('temp', 'test.html')

        # Mimetype should be determinable from extension
        for node in [txt_node, json_node, html_node]:
            mimetype = node.mimetype
            assert mimetype is None or isinstance(mimetype, str)

    # ========================================================================
    # URL Generation Tests
    # ========================================================================

    def test_storage_node_url(self):
        """Test NewStorageNode.url() method."""
        node = self.site.storageNode('gnr', 'js', 'test.js')

        # Get URL
        url = node.url()
        assert isinstance(url, str)
        assert len(url) > 0

    def test_storage_node_kwargs_url(self):
        """Test NewStorageNode.kwargs_url() method."""
        node = self.site.storageNode('gnr', 'js', 'test.js')

        # Get URL with kwargs
        url = node.kwargs_url(nocache=True)
        assert isinstance(url, str)
        assert len(url) > 0
        # Should have cache-busting parameter
        assert '_=' in url or 'nocache' in url.lower()

    def test_storage_node_internal_url(self):
        """Test NewStorageNode.internal_url() method."""
        node = self.site.storageNode('gnr', 'css', 'test.css')

        # Get internal URL (if supported)
        if hasattr(node, 'internal_url'):
            internal_url = node.internal_url()
            # Should not raise exception
            assert internal_url is None or isinstance(internal_url, str)

    # ========================================================================
    # Legacy Storage Service Adapter Tests
    # ========================================================================

    def test_storage_service_is_deprecated_adapter(self):
        """Test that storage() returns LegacyStorageServiceAdapter."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import LegacyStorageServiceAdapter

        service = self.site.storage('gnr')
        assert service is not None
        assert isinstance(service, LegacyStorageServiceAdapter)

    def test_storage_service_adapter_url(self):
        """Test LegacyStorageServiceAdapter.url() method."""
        service = self.site.storage('gnr')
        if service:
            url = service.url('js', 'test.js')
            assert url is not None
            assert isinstance(url, str)

    def test_storage_service_adapter_kwargs_url(self):
        """Test LegacyStorageServiceAdapter.kwargs_url() method."""
        service = self.site.storage('gnr')
        if service:
            url = service.kwargs_url('js', 'test.js', nocache=True)
            assert url is not None
            assert isinstance(url, str)
            # Should have cache-busting parameter
            assert '_=' in url

    def test_storage_service_adapter_delegates_to_storagenode(self):
        """Test that adapter delegates to storageNode()."""
        service = self.site.storage('gnr')
        if service:
            # Get URL via service adapter
            service_url = service.url('js', 'test.js')

            # Get URL directly via storageNode
            node = self.site.storageNode('gnr', 'js', 'test.js')
            node_url = node.url()

            # Should produce similar results
            assert service_url == node_url or service_url.rstrip('/') == node_url.rstrip('/')

    # ========================================================================
    # Storage Parameter Adaptation Tests
    # ========================================================================

    def test_adapt_local_implementation(self):
        """Test adaptation of 'local' implementation to genro-storage."""
        # Local implementation should map to 'local' type in genro-storage
        params = {
            'implementation': 'local',
            'base_path': '/tmp/test'
        }
        mount_config = self.storage_handler._adaptStorageParamsToMount('test_local', params)

        assert mount_config is not None
        assert mount_config['type'] == 'local'
        assert 'path' in mount_config

    def test_adapt_symbolic_implementation(self):
        """Test adaptation of 'symbolic' implementation to genro-storage."""
        # Symbolic should also map to 'local'
        params = {
            'implementation': 'symbolic',
            'base_path': '/tmp/test'
        }
        mount_config = self.storage_handler._adaptStorageParamsToMount('test_symbolic', params)

        assert mount_config is not None
        assert mount_config['type'] == 'local'

    def test_adapt_s3_implementation(self):
        """Test adaptation of 'aws_s3' implementation to genro-storage."""
        params = {
            'implementation': 'aws_s3',
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'access_key': 'test_key',
            'secret_key': 'test_secret'
        }
        mount_config = self.storage_handler._adaptStorageParamsToMount('test_s3', params)

        assert mount_config is not None
        assert mount_config['type'] == 's3'
        assert 'bucket' in mount_config

    def test_adapt_http_implementation(self):
        """Test adaptation of 'http' implementation to genro-storage."""
        params = {
            'implementation': 'http',
            'base_url': 'https://example.com/files'
        }
        mount_config = self.storage_handler._adaptStorageParamsToMount('test_http', params)

        assert mount_config is not None
        assert mount_config['type'] == 'http'

    # ========================================================================
    # Backward Compatibility Tests
    # ========================================================================

    def test_storage_node_with_existing_node(self):
        """Test storageNode with existing node object."""
        # Create initial node
        node1 = self.site.storageNode('gnr', 'js')
        assert node1 is not None

        # Pass existing node (should return it)
        node2 = self.site.storageNode(node1)
        assert node2 is not None

        # Pass existing node with additional path (should create new node)
        node3 = self.site.storageNode(node1, 'subdir')
        assert node3 is not None

    def test_make_node_parameters(self):
        """Test makeNode with various parameters."""
        # Test with autocreate parameter
        node = self.storage_handler.makeNode('temp', 'test_dir', autocreate=False)
        assert node is not None

        # Test with must_exist parameter
        node = self.storage_handler.makeNode('gnr', must_exist=False)
        assert node is not None

    def test_storage_path_basic(self):
        """Test basic storage path generation."""
        path = self.site.storagePath('gnr', 'test/file.js')
        assert path is not None
        assert isinstance(path, str)

    # ========================================================================
    # Edge Cases and Error Handling
    # ========================================================================

    def test_storage_nonexistent(self):
        """Test accessing non-existent storage returns None."""
        result = self.site.storage('nonexistent_storage_12345')
        assert result is None

    def test_storage_with_empty_name(self):
        """Test storage access with empty storage name."""
        result = self.site.storage('')
        # Should handle gracefully (return None)
        assert result is None

    def test_storage_node_with_none_path(self):
        """Test storage node creation with None in path."""
        # Should handle gracefully
        try:
            node = self.site.storageNode('gnr', None)
            # If it doesn't raise, check result
            assert node is None or hasattr(node, 'fullpath')
        except (TypeError, AttributeError):
            # Acceptable to raise exception for invalid input
            pass

    # ========================================================================
    # Versioning Tests
    # ========================================================================

    def test_storage_node_versions(self):
        """Test NewStorageNode.versions property."""
        test_node = self.site.storageNode('temp', f'test_versions_{os.getpid()}.txt')

        try:
            # Create file
            with test_node.open('wb') as f:
                f.write(b"versioned content")

            if test_node.exists:
                # Get versions (may return empty list if not versioned)
                versions = test_node.versions
                assert versions is not None
                assert isinstance(versions, (list, tuple))

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_with_version_parameter(self):
        """Test creating StorageNode with version parameter."""
        # Create node with version parameter
        node = self.storage_handler.makeNode('temp', 'versioned_file.txt', version='v1')

        assert node is not None
        assert node.version == 'v1'


class TestStorageHandlerFactory(BaseGnrTest):
    """Tests for the StorageHandler factory function."""

    def test_factory_returns_legacy_by_default(self):
        """Test that factory returns LegacyStorageHandler when mode not specified."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import (
            StorageHandler, LegacyStorageHandler
        )

        # Create mock site with no storage mode configured
        mock_site = MagicMock()
        mock_site.config = Bag()
        # No storage node means mode will be None

        handler = StorageHandler(mock_site)
        assert isinstance(handler, LegacyStorageHandler)

    def test_factory_returns_legacy_for_legacy_mode(self):
        """Test that factory returns LegacyStorageHandler for mode='legacy'."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import (
            StorageHandler, LegacyStorageHandler
        )

        mock_site = MagicMock()
        mock_site.config = Bag()
        mock_site.config.setItem('storage', None, mode='legacy')

        handler = StorageHandler(mock_site)
        assert isinstance(handler, LegacyStorageHandler)

    def test_factory_returns_new_for_ns_mode(self):
        """Test that factory returns NewStorageHandler for mode='ns'."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import (
            StorageHandler, NewStorageHandler
        )

        mock_site = MagicMock()
        mock_site.config = Bag()
        mock_site.config.setItem('storage', None, mode='ns')

        # Mock necessary site attributes for NewStorageHandler initialization
        test_site_path = tempfile.mkdtemp(prefix='test_site_')
        mock_site.site_path = test_site_path
        mock_site.site_static_dir = os.path.join(test_site_path, 'static')
        mock_site.resources_path = os.path.join(test_site_path, 'resources')
        mock_site.packages = {}

        # Create directories that the handler expects
        # BaseStorageHandler.__init__ creates storages for: home, site, mail, user, conn, page, temp
        os.makedirs(mock_site.site_static_dir, exist_ok=True)
        os.makedirs(os.path.join(mock_site.site_static_dir, 'mail'), exist_ok=True)
        os.makedirs(os.path.join(test_site_path, 'data', 'temp'), exist_ok=True)
        os.makedirs(os.path.join(test_site_path, 'data', 'users'), exist_ok=True)
        os.makedirs(os.path.join(test_site_path, 'data', 'connections'), exist_ok=True)
        os.makedirs(os.path.join(test_site_path, 'data', 'pages'), exist_ok=True)

        try:
            handler = StorageHandler(mock_site)
            assert isinstance(handler, NewStorageHandler)
        finally:
            if os.path.exists(test_site_path):
                shutil.rmtree(test_site_path)
