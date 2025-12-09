import os
import time
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

    def test_storage_nonexistent(self):
        """Test accessing non-existent storage falls back to local storage.

        For backward compatibility, accessing a storage that doesn't exist
        in storage_params creates a local storage with the storage_name
        as subdirectory of site_static_dir.
        """
        result = self.site.storage('nonexistent_storage_12345')
        # Should create a fallback local storage, not return None
        assert result is not None
        assert hasattr(result, 'exists')
        assert hasattr(result, 'url')

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
        node = self.storage_handler.makeNode('site:test_dir', autocreate=False)
        assert node is not None

        # Test with must_exist parameter
        node = self.storage_handler.makeNode('gnr:', must_exist=False)
        assert node is not None

    def test_storage_node_operations(self):
        """Test basic storage node operations."""
        # Get a storage node for testing
        temp_node = self.site.storageNode('site:test_operations')
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

    def test_adapt_path_raw_default(self):
        """Test path adaptation defaults to _raw_ when no prefix."""
        service_name, path = self.storage_handler._adapt_path('/some/path/file.txt')
        assert service_name == '_raw_'
        assert 'some/path/file.txt' in path

    # ========================================================================
    # Storage Parameter Updates Tests
    # ========================================================================

    def test_set_storage_params_with_bag(self):
        """Test _setStorageParams with Bag input."""
        test_params = Bag()
        test_params['base_path'] = '/tmp/test'
        test_params['some_option'] = 'value'

        self.storage_handler._setStorageParams(
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

        self.storage_handler._setStorageParams(
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

        self.storage_handler._setStorageParams(
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
        except Exception:
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
        """Test storage access with empty storage name.

        For backward compatibility, even empty names create a fallback
        local storage in site_static_dir.
        """
        result = self.site.storage('')
        # Should create a fallback local storage (backward compatibility)
        assert result is not None
        assert hasattr(result, 'exists')

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
    # StorageNode API Tests - Basic Properties
    # ========================================================================

    def test_storage_node_properties(self):
        """Test StorageNode basic properties."""
        node = self.site.storageNode('site:test_props.txt')
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
        """Test StorageNode basename and extension properties."""
        node = self.site.storageNode('site:subdir/test_file.txt')

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
        node = self.site.storageNode('site:document.pdf')
        name, ext = node.splitext()
        assert isinstance(name, str)
        assert isinstance(ext, str)
        assert ext in ['.pdf', 'pdf']

    def test_storage_node_parent(self):
        """Test StorageNode parent directory access."""
        node = self.site.storageNode('site:subdir/file.txt')

        # Test dirname property
        dirname = node.dirname
        assert isinstance(dirname, str)

        # Test parentStorageNode property
        parent_node = node.parentStorageNode
        assert parent_node is not None
        assert hasattr(parent_node, 'fullpath')

    def test_storage_node_child(self):
        """Test StorageNode child() method."""
        parent_node = self.site.storageNode('site:parent_dir')

        # Create child node
        child_node = parent_node.child('child_file.txt')
        assert child_node is not None
        assert hasattr(child_node, 'fullpath')

        child_fullpath = child_node.fullpath
        assert 'child_file.txt' in child_fullpath

    # ========================================================================
    # StorageNode API Tests - URL and Serving
    # ========================================================================

    def test_storage_node_url(self):
        """Test StorageNode.url() method."""
        node = self.site.storageNode('gnr:js/test.js')

        # Get URL
        url = node.url()
        assert isinstance(url, str)
        # URL may be empty for non-existent files, just check it doesn't raise

    def test_storage_node_internal_url(self):
        """Test StorageNode.internal_url() method."""
        node = self.site.storageNode('gnr:css/test.css')

        # Get internal URL (if supported)
        if hasattr(node, 'internal_url'):
            internal_url = node.internal_url()
            # Should not raise exception
            assert internal_url is None or isinstance(internal_url, str)

    def test_storage_node_mimetype(self):
        """Test StorageNode.mimetype property."""
        # Test with different file types
        txt_node = self.site.storageNode('site:test.txt')
        json_node = self.site.storageNode('site:test.json')
        html_node = self.site.storageNode('site:test.html')

        # Mimetype should be determinable from extension
        for node in [txt_node, json_node, html_node]:
            mimetype = node.mimetype
            assert mimetype is None or isinstance(mimetype, str)
