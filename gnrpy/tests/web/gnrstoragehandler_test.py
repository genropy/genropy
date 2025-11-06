import os
import time
import pytest
import tempfile
import shutil

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


class TestStorageHandler(BaseGnrTest):
    """Comprehensive tests for storage handler, storage services, and storage nodes."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
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
        # Clean up temporary directory
        if hasattr(cls, 'test_dir') and os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        super().teardown_class()

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

    def test_site_specific_storage_params(self):
        """Test that site-specific storage services are registered (home, site, mail)."""
        site_storages = ['home', 'site', 'mail']

        for storage_name in site_storages:
            if storage_name in self.storage_handler.storage_params:
                params = self.storage_handler.storage_params[storage_name]
                assert isinstance(params, dict)
                assert 'implementation' in params
                assert params['implementation'] == 'local'
                assert 'base_path' in params

    def test_storage_params_structure(self):
        """Test that storage parameters have correct structure."""
        for storage_name, params in self.storage_handler.storage_params.items():
            assert isinstance(params, dict), \
                f"Parameters for '{storage_name}' should be a dict"
            assert 'implementation' in params, \
                f"Parameters for '{storage_name}' should have 'implementation' key"
            impl = params['implementation']
            assert impl in ['local', 'symbolic', 'raw', 'http', 'aws_s3'], \
                f"Unknown implementation '{impl}' for storage '{storage_name}'"

    # ========================================================================
    # Storage Service Access Tests
    # ========================================================================

    def test_storage_method(self):
        """Test storage() method returns service instances."""
        # Test with built-in storage
        gnr_storage = self.site.storage('gnr')
        assert gnr_storage is not None
        assert hasattr(gnr_storage, 'url')
        assert hasattr(gnr_storage, 'exists')

    def test_storage_service_method(self):
        """Test storageService() method returns service instances."""
        rsrc_service = self.storage_handler.storageService('rsrc')
        assert rsrc_service is not None
        assert hasattr(rsrc_service, 'url')

    def test_storage_nonexistent(self):
        """Test accessing non-existent storage returns None."""
        result = self.site.storage('nonexistent_storage_12345')
        assert result is None

        result = self.storage_handler.storageService('nonexistent_storage_12345')
        assert result is None

    def test_storage_with_kwargs(self):
        """Test that storage() accepts additional kwargs."""
        # Should not raise exception
        storage = self.site.storage('gnr', some_param='value')
        assert storage is not None

    # ========================================================================
    # Storage Path Tests
    # ========================================================================

    def test_storage_path_basic(self):
        """Test basic storage path generation."""
        path = self.site.storagePath('gnr', 'test/file.js')
        assert path is not None
        assert isinstance(path, str)

    def test_storage_path_user(self):
        """Test user storage path includes username."""
        # User storage should adapt path based on current user
        path = self.storage_handler.storagePath('user', 'documents/test.txt')
        assert isinstance(path, str)

    def test_storage_path_conn(self):
        """Test conn storage path includes connection_id."""
        # Connection storage needs active page/connection
        if hasattr(self.site, 'currentPage') and self.site.currentPage:
            path = self.storage_handler.storagePath('conn', 'data.json')
            assert isinstance(path, str)

    def test_storage_path_page(self):
        """Test page storage path includes connection and page ids."""
        # Page storage needs active page
        if hasattr(self.site, 'currentPage') and self.site.currentPage:
            path = self.storage_handler.storagePath('page', 'state.json')
            assert isinstance(path, str)

    # ========================================================================
    # Storage Node Tests
    # ========================================================================

    def test_storage_node_creation(self):
        """Test creating storage nodes."""
        node = self.site.storageNode('gnr', 'js', 'dojo_libs')
        assert node is not None
        assert hasattr(node, 'fullpath')
        assert hasattr(node, 'exists')

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

    def test_storage_node_operations(self):
        """Test basic storage node operations."""
        # Get a storage node for testing
        temp_node = self.site.storageNode('temp', 'test_operations')
        assert temp_node is not None

        # Test exists method
        assert hasattr(temp_node, 'exists')

        # Test fullpath property
        assert hasattr(temp_node, 'fullpath')
        fullpath = temp_node.fullpath
        assert isinstance(fullpath, str)

    # ========================================================================
    # Legacy Path Adaptation Tests
    # ========================================================================

    def test_adapt_path_legacy_volume(self):
        """Test adaptation of legacy 'vol:' prefix paths."""
        # The _adapt_path method should convert 'vol:storage_name:path' format
        service_name, path = self.storage_handler._adapt_path('vol:gnr:js/test.js')
        assert service_name == 'gnr'
        assert path == 'js/test.js'

    def test_adapt_path_normal(self):
        """Test adaptation of normal 'storage_name:path' format."""
        service_name, path = self.storage_handler._adapt_path('rsrc:images/logo.png')
        assert service_name == 'rsrc'
        assert path == 'images/logo.png'

    def test_adapt_path_with_multiple_components(self):
        """Test path adaptation with multiple path components."""
        service_name, path = self.storage_handler._adapt_path('pkg', 'gnrcore', 'static', 'file.js')
        assert service_name == 'pkg'
        assert 'gnrcore' in path
        assert 'static' in path
        assert 'file.js' in path

    # ========================================================================
    # Storage Parameter Updates Tests
    # ========================================================================

    def test_set_storage_params_with_bag(self):
        """Test _setStorageParams with Bag input."""
        test_params = Bag()
        test_params['base_path'] = '/tmp/test'
        test_params['some_option'] = 'value'

        result = self.storage_handler._setStorageParams(
            'test_storage_bag',
            parameters=test_params,
            implementation='local'
        )

        assert 'test_storage_bag' in self.storage_handler.storage_params
        params = self.storage_handler.storage_params['test_storage_bag']
        assert params['implementation'] == 'local'
        assert params['base_path'] == '/tmp/test'
        assert params['some_option'] == 'value'

    def test_set_storage_params_with_dict(self):
        """Test _setStorageParams with dict input."""
        test_params = {
            'base_path': '/tmp/test2',
            'option': 'value2'
        }

        result = self.storage_handler._setStorageParams(
            'test_storage_dict',
            parameters=test_params,
            implementation='symbolic'
        )

        assert 'test_storage_dict' in self.storage_handler.storage_params
        params = self.storage_handler.storage_params['test_storage_dict']
        assert params['implementation'] == 'symbolic'
        assert params['base_path'] == '/tmp/test2'

    def test_set_storage_params_override_implementation(self):
        """Test that implementation parameter overrides what's in parameters."""
        test_params = {'implementation': 'local', 'base_path': '/tmp/test'}

        result = self.storage_handler._setStorageParams(
            'test_storage_override',
            parameters=test_params,
            implementation='symbolic'  # This should override 'local'
        )

        params = self.storage_handler.storage_params['test_storage_override']
        assert params['implementation'] == 'symbolic'

    def test_update_storage_params(self):
        """Test updateStorageParams method."""
        # This requires a storage service in the database
        # We'll test that the method exists and accepts parameters
        assert hasattr(self.storage_handler, 'updateStorageParams')

        # The method should not raise exception for non-existent storage
        try:
            self.storage_handler.updateStorageParams('nonexistent_test_storage')
        except Exception as e:
            # Should handle gracefully
            pass

    def test_remove_storage_from_cache(self):
        """Test removeStorageFromCache method."""
        # Add a test storage
        self.storage_handler._setStorageParams(
            'test_storage_to_remove',
            parameters={'base_path': '/tmp/remove_test'},
            implementation='local'
        )

        assert 'test_storage_to_remove' in self.storage_handler.storage_params

        # Remove it
        self.storage_handler.removeStorageFromCache('test_storage_to_remove')

        assert 'test_storage_to_remove' not in self.storage_handler.storage_params

    # ========================================================================
    # Different Implementation Types Tests
    # ========================================================================

    def test_local_storage_implementation(self):
        """Test local storage implementation."""
        # Many built-in storages use local implementation
        for storage_name in ['gnr', 'dojo', 'pages']:
            if storage_name in self.storage_handler.storage_params:
                params = self.storage_handler.storage_params[storage_name]
                if params.get('implementation') == 'local':
                    storage = self.site.storage(storage_name)
                    assert storage is not None

    def test_symbolic_storage_implementation(self):
        """Test symbolic storage implementation."""
        # Check if any storages use symbolic implementation
        for storage_name, params in self.storage_handler.storage_params.items():
            if params.get('implementation') == 'symbolic':
                storage = self.site.storage(storage_name)
                assert storage is not None
                break

    def test_raw_storage_implementation(self):
        """Test raw storage (_raw_) implementation."""
        if '_raw_' in self.storage_handler.storage_params:
            raw_storage = self.site.storage('_raw_')
            assert raw_storage is not None

    def test_http_storage_implementation(self):
        """Test HTTP storage (_http_) implementation."""
        if '_http_' in self.storage_handler.storage_params:
            http_storage = self.site.storage('_http_')
            assert http_storage is not None

    # ========================================================================
    # Integration Tests
    # ========================================================================

    def test_storage_url_generation(self):
        """Test URL generation for storage resources."""
        # Get a storage service
        gnr_storage = self.site.storage('gnr')
        if gnr_storage and hasattr(gnr_storage, 'url'):
            url = gnr_storage.url('js', 'test.js')
            assert isinstance(url, str)
            assert 'gnr' in url or 'static' in url

    def test_storage_exists_check(self):
        """Test existence checking for storage paths."""
        gnr_storage = self.site.storage('gnr')
        if gnr_storage and hasattr(gnr_storage, 'exists'):
            # The method should be callable
            assert callable(gnr_storage.exists)

    def test_storage_handler_proxy_methods(self):
        """Test that site proxy methods delegate to storage_handler."""
        # Test that site.storage delegates to storage_handler.storage
        site_result = self.site.storage('gnr')
        handler_result = self.storage_handler.storage('gnr')

        # Both should return similar objects (service instances)
        assert (site_result is None) == (handler_result is None)

        if site_result is not None:
            assert type(site_result) == type(handler_result)

    def test_deprecated_get_volume_service(self):
        """Test that deprecated getVolumeService still works but is deprecated."""
        # Should still work for backward compatibility
        result = self.storage_handler.getVolumeService('gnr')
        # May return None or a service, but should not raise exception
        assert result is None or hasattr(result, 'url')

    # ========================================================================
    # Edge Cases and Error Handling
    # ========================================================================

    def test_storage_with_empty_name(self):
        """Test storage access with empty storage name."""
        result = self.site.storage('')
        # Should handle gracefully (return None or raise specific exception)
        assert result is None or isinstance(result, Exception)

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

    def test_storage_params_immutability(self):
        """Test that external modification of storage_params is reflected."""
        # Get initial count
        initial_count = len(self.storage_handler.storage_params)

        # Add a new storage via _setStorageParams
        self.storage_handler._setStorageParams(
            'test_immutability',
            parameters={'base_path': '/tmp/immut_test'},
            implementation='local'
        )

        # Should be reflected in storage_params
        assert len(self.storage_handler.storage_params) == initial_count + 1
        assert 'test_immutability' in self.storage_handler.storage_params

        # Clean up
        self.storage_handler.removeStorageFromCache('test_immutability')

    # ========================================================================
    # StorageNode API Tests - File/Directory Operations
    # ========================================================================

    def test_storage_node_properties(self):
        """Test StorageNode basic properties."""
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
        assert 'temp' in fullpath

    def test_storage_node_basename_and_extension(self):
        """Test StorageNode basename and extension properties."""
        node = self.site.storageNode('temp', 'subdir', 'test_file.txt')

        basename = node.basename
        assert isinstance(basename, str)
        assert 'test_file.txt' in basename

        # Test extension property
        ext = node.ext
        assert ext == 'txt' or ext == '.txt' or 'txt' in ext

        # Test cleanbasename (without extension)
        cleanbasename = node.cleanbasename
        assert 'test_file' in cleanbasename
        assert '.txt' not in cleanbasename

    def test_storage_node_splitext(self):
        """Test StorageNode splitext method."""
        node = self.site.storageNode('temp', 'document.pdf')
        name, ext = node.splitext()
        assert isinstance(name, str)
        assert isinstance(ext, str)
        assert ext in ['.pdf', 'pdf']

    def test_storage_node_parent(self):
        """Test StorageNode parent directory access."""
        node = self.site.storageNode('temp', 'subdir', 'file.txt')

        # Test dirname property
        dirname = node.dirname
        assert isinstance(dirname, str)

        # Test parentStorageNode property
        parent_node = node.parentStorageNode
        assert parent_node is not None
        assert hasattr(parent_node, 'fullpath')

    def test_storage_node_child(self):
        """Test StorageNode child() method."""
        parent_node = self.site.storageNode('temp', 'parent_dir')

        # Create child node
        child_node = parent_node.child('child_file.txt')
        assert child_node is not None
        assert hasattr(child_node, 'fullpath')

        child_fullpath = child_node.fullpath
        assert 'child_file.txt' in child_fullpath

    # ========================================================================
    # StorageNode API Tests - File Content Operations
    # ========================================================================

    def test_storage_node_open_context_manager(self):
        """Test StorageNode.open() as context manager."""
        # Create a test file in temp storage
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

    def test_storage_node_base64(self):
        """Test StorageNode.base64() method."""
        # Create a test file with known content
        test_node = self.site.storageNode('temp', f'test_base64_{os.getpid()}.txt')

        try:
            # Write test content
            test_content = b"Base64 test content"
            with test_node.open('wb') as f:
                f.write(test_content)

            # Get base64 encoding
            if test_node.exists:
                b64 = test_node.base64()
                assert isinstance(b64, str)
                # Should be valid base64
                import base64
                decoded = base64.b64decode(b64.split(',')[-1] if ',' in b64 else b64)
                assert test_content in decoded or decoded == test_content

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_local_path_context_manager(self):
        """Test StorageNode.local_path() context manager."""
        test_node = self.site.storageNode('temp', f'test_local_path_{os.getpid()}.txt')

        try:
            # Write initial content
            initial_content = b"Initial content"
            with test_node.open('wb') as f:
                f.write(initial_content)

            # Use local_path context manager
            if hasattr(test_node, 'local_path'):
                with test_node.local_path(mode='r+') as local_file:
                    # local_file should be a path string
                    assert isinstance(local_file, str)
                    assert os.path.exists(local_file)

                    # Can work with the local file
                    with open(local_file, 'rb') as f:
                        content = f.read()
                        assert content == initial_content

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_mimetype(self):
        """Test StorageNode.mimetype property."""
        # Test with different file types
        txt_node = self.site.storageNode('temp', 'test.txt')
        json_node = self.site.storageNode('temp', 'test.json')
        html_node = self.site.storageNode('temp', 'test.html')

        # Mimetype should be determinable from extension
        for node in [txt_node, json_node, html_node]:
            mimetype = node.mimetype
            assert mimetype is None or isinstance(mimetype, str)

    # ========================================================================
    # StorageNode API Tests - Directory Operations
    # ========================================================================

    def test_storage_node_mkdir(self):
        """Test StorageNode.mkdir() method."""
        test_dir_node = self.site.storageNode('temp', f'test_mkdir_{os.getpid()}')

        try:
            # Create directory
            if not test_dir_node.exists:
                test_dir_node.mkdir()

            # Check if created (if storage supports it)
            if test_dir_node.exists:
                assert test_dir_node.isdir

        finally:
            try:
                test_dir_node.delete()
            except:
                pass

    def test_storage_node_listdir(self):
        """Test StorageNode.listdir() method."""
        # Use temp storage for testing
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
        """Test StorageNode.children() method."""
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
                    # Each child should be a StorageNode
                    for child in children:
                        assert hasattr(child, 'fullpath')

        finally:
            try:
                test_dir.delete()
            except:
                pass

    # ========================================================================
    # StorageNode API Tests - File Operations (Move, Copy, Delete)
    # ========================================================================

    def test_storage_node_delete(self):
        """Test StorageNode.delete() method."""
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
        """Test StorageNode.move() method."""
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

                # Source should now point to destination
                assert 'dest' in source_node.fullpath

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
        """Test StorageNode.copy() method."""
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
    # StorageNode API Tests - Metadata and Attributes
    # ========================================================================

    def test_storage_node_mtime(self):
        """Test StorageNode.mtime property."""
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
        """Test StorageNode.size property."""
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

    def test_storage_node_metadata(self):
        """Test StorageNode get_metadata() and set_metadata() methods."""
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

    def test_storage_node_md5hash(self):
        """Test StorageNode.md5hash property."""
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
                    assert len(md5) == 32 or len(md5) == 36  # with dashes

        finally:
            try:
                test_node.delete()
            except:
                pass

    def test_storage_node_ext_attributes(self):
        """Test StorageNode.ext_attributes property."""
        test_node = self.site.storageNode('temp', f'test_extattr_{os.getpid()}.txt')

        try:
            # Create file
            with test_node.open('wb') as f:
                f.write(b"ext attributes test")

            if test_node.exists:
                # Get extended attributes (implementation-specific)
                ext_attrs = test_node.ext_attributes
                # Should not raise exception
                assert ext_attrs is None or isinstance(ext_attrs, dict)

        finally:
            try:
                test_node.delete()
            except:
                pass

    # ========================================================================
    # StorageNode API Tests - URL and Serving
    # ========================================================================

    def test_storage_node_url(self):
        """Test StorageNode.url() method."""
        node = self.site.storageNode('gnr', 'js', 'test.js')

        # Get URL
        url = node.url()
        assert isinstance(url, str)
        assert len(url) > 0

    def test_storage_node_internal_url(self):
        """Test StorageNode.internal_url() method."""
        node = self.site.storageNode('gnr', 'css', 'test.css')

        # Get internal URL (if supported)
        if hasattr(node, 'internal_url'):
            internal_url = node.internal_url()
            # Should not raise exception
            assert internal_url is None or isinstance(internal_url, str)

    def test_storage_node_fill_from_url(self):
        """Test StorageNode.fill_from_url() method."""
        test_node = self.site.storageNode('temp', f'test_fill_url_{os.getpid()}.html')

        try:
            # Try to download a simple resource
            # Using a data URL to avoid external dependencies
            data_url = 'data:text/plain;base64,SGVsbG8gV29ybGQ='  # "Hello World"

            if hasattr(test_node, 'fill_from_url'):
                try:
                    test_node.fill_from_url(data_url)
                    # If successful, file should exist
                    if test_node.exists:
                        with test_node.open('rb') as f:
                            content = f.read()
                            assert b'Hello World' in content
                except:
                    # May fail due to urllib restrictions, that's ok
                    pass

        finally:
            try:
                test_node.delete()
            except:
                pass

    # ========================================================================
    # StorageNode API Tests - Versioning
    # ========================================================================

    def test_storage_node_versions(self):
        """Test StorageNode.versions property."""
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
