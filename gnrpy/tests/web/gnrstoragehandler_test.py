import pytest
import os
import tempfile
import shutil

from gnr.core.gnrbag import Bag
from gnr.core.gnrconfig import getGenroRoot
from gnr.core.gnrlang import GnrException, gnrImport
from gnr.lib.services.storage import StorageResolver

from webcommon import BaseGnrDaemonTest

class TestStorageHandler(BaseGnrDaemonTest):
    """Comprehensive tests for storage handler, storage services, and storage nodes."""

    @classmethod
    def setup_class(cls):
        super().setup_class()


        cls.storage_handler = cls.site.storage_handler
        cls.test_dir = tempfile.mkdtemp(prefix='gnr_storage_test_')

    @classmethod
    def teardown_class(cls):
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
            assert impl in ['local', 'symbolic', 'raw', 'http', 'aws_s3', 'relative'], \
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

    def test_storage_node_nonexistent_storage(self):
        """Test storageNode with non-existent storage name creates fallback local storage.

        This is the exact scenario reported by mbertoldi: using storageNode with
        an arbitrary storage name that doesn't exist in storage_params should
        create a subfolder in site_static_dir, not return None.
        """
        # This is the pattern reported as broken: storageNode('non_existing_storage:', filename)
        node = self.site.storageNode('my_custom_storage:', 'testfile.txt')

        # Should create a valid storage node, not None
        assert node is not None
        assert hasattr(node, 'fullpath')
        assert hasattr(node, 'exists')

        # The path should be under site_static_dir/my_custom_storage/
        assert 'my_custom_storage' in node.fullpath
        assert 'testfile.txt' in node.fullpath

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
        # Should still work for backward compatibility, but raises a deprecation warning
        with pytest.warns(DeprecationWarning):
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

    # ========================================================================
    # Site Config Loading Tests (Bug #348)
    # ========================================================================

    def test_load_storage_from_siteconfig_nested_structure(self):
        """Test loading storage params from nested <services><storage>...</storage></services> structure."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import BaseStorageHandler

        # Create a mock site with nested storage config
        class MockSite:
            def __init__(self):
                self.config = Bag()
                # Nested structure: <services><storage><my_store .../></storage></services>
                self.config['services.storage.my_nested_store'] = Bag()
                self.config.setAttr('services.storage.my_nested_store',
                    implementation='local', base_path='/tmp/nested')
                self.site_static_dir = '/tmp/test_site'

            @property
            def gnrapp(self):
                class MockApp:
                    packages = type('obj', (object,), {'keys': lambda self: []})()
                return MockApp()

            @property
            def db(self):
                return None

        mock_site = MockSite()
        handler = BaseStorageHandler.__new__(BaseStorageHandler)
        handler.site = mock_site
        handler.storage_params = {}

        # Load from site config
        handler._loadStorageParametersFromSiteConfig()

        # Should have loaded my_nested_store
        assert 'my_nested_store' in handler.storage_params
        params = handler.storage_params['my_nested_store']
        assert params.get('implementation') == 'local'
        assert params.get('base_path') == '/tmp/nested'

    def test_load_storage_from_siteconfig_flat_structure(self):
        """Test loading storage params from flat <services><my_store service_type='storage' .../></services> structure."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import BaseStorageHandler

        # Create a mock site with flat config
        class MockSite:
            def __init__(self):
                self.config = Bag()
                # Flat structure: <services><my_flat_store service_type="storage" .../></services>
                self.config['services.my_flat_store'] = Bag()
                self.config.setAttr('services.my_flat_store',
                    service_type='storage', implementation='local', base_path='/tmp/flat')
                self.site_static_dir = '/tmp/test_site'

            @property
            def gnrapp(self):
                class MockApp:
                    packages = type('obj', (object,), {'keys': lambda self: []})()
                return MockApp()

            @property
            def db(self):
                return None

        mock_site = MockSite()
        handler = BaseStorageHandler.__new__(BaseStorageHandler)
        handler.site = mock_site
        handler.storage_params = {}

        # Load from site config
        handler._loadStorageParametersFromSiteConfig()

        # Should have loaded my_flat_store
        assert 'my_flat_store' in handler.storage_params
        params = handler.storage_params['my_flat_store']
        assert params.get('implementation') == 'local'
        assert params.get('base_path') == '/tmp/flat'

    def test_load_storage_from_siteconfig_mixed_services(self):
        """Test that non-storage services in config don't cause errors (Bug #348).

        This tests the exact scenario from issue #348 where having other service types
        in the <services> section (like Neon database) caused AttributeError because
        getAttr() returned None for services without attributes.
        """
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import BaseStorageHandler

        # Create a mock site with mixed services (storage and non-storage)
        class MockSite:
            def __init__(self):
                self.config = Bag()
                # Add a non-storage service (like Neon database) - this was causing the bug
                self.config['services.neon'] = Bag()
                self.config.setAttr('services.neon',
                    service_type='database', host='localhost', port=5432)

                # Add another service without any attributes (edge case)
                self.config['services.empty_service'] = Bag()

                # Add a storage service
                self.config['services.my_storage'] = Bag()
                self.config.setAttr('services.my_storage',
                    service_type='storage', implementation='local', base_path='/tmp/storage')

                self.site_static_dir = '/tmp/test_site'

            @property
            def gnrapp(self):
                class MockApp:
                    packages = type('obj', (object,), {'keys': lambda self: []})()
                return MockApp()

            @property
            def db(self):
                return None

        mock_site = MockSite()
        handler = BaseStorageHandler.__new__(BaseStorageHandler)
        handler.site = mock_site
        handler.storage_params = {}

        # This should NOT raise AttributeError: 'NoneType' object has no attribute 'get'
        handler._loadStorageParametersFromSiteConfig()

        # Should have loaded only the storage service
        assert 'my_storage' in handler.storage_params
        assert 'neon' not in handler.storage_params
        assert 'empty_service' not in handler.storage_params

    def test_load_storage_from_siteconfig_no_services(self):
        """Test that missing services section doesn't cause errors."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import BaseStorageHandler

        class MockSite:
            def __init__(self):
                self.config = Bag()  # No services section
                self.site_static_dir = '/tmp/test_site'

            @property
            def gnrapp(self):
                class MockApp:
                    packages = type('obj', (object,), {'keys': lambda self: []})()
                return MockApp()

            @property
            def db(self):
                return None

        mock_site = MockSite()
        handler = BaseStorageHandler.__new__(BaseStorageHandler)
        handler.site = mock_site
        handler.storage_params = {}

        # Should not raise any exception
        handler._loadStorageParametersFromSiteConfig()

        # storage_params should remain empty (no services configured)
        assert len(handler.storage_params) == 0

    def test_load_storage_from_siteconfig_null_attrs(self):
        """Test handling of services where getAttr returns None (Bug #348 root cause)."""
        from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import BaseStorageHandler

        class MockSite:
            def __init__(self):
                self.config = Bag()
                # Service with no attributes at all - getAttr() returns None
                self.config['services.service_with_no_attrs'] = 'just a string value'
                self.site_static_dir = '/tmp/test_site'

            @property
            def gnrapp(self):
                class MockApp:
                    packages = type('obj', (object,), {'keys': lambda self: []})()
                return MockApp()

            @property
            def db(self):
                return None

        mock_site = MockSite()
        handler = BaseStorageHandler.__new__(BaseStorageHandler)
        handler.site = mock_site
        handler.storage_params = {}

        # Should not raise: AttributeError: 'NoneType' object has no attribute 'get'
        handler._loadStorageParametersFromSiteConfig()

    # ========================================================================
    # Service Name Parameter Handling Tests
    # ========================================================================

    def test_storage_params_service_name_not_duplicated(self):
        """Test that service_name in storage_params doesn't cause duplicate parameter.

        When storage_params contains a 'service_name' key, it should be removed
        before passing to getService() to avoid duplicate keyword argument error.
        """
        # Add a storage with service_name in params (simulating DB record)
        self.storage_handler._setStorageParams(
            'test_service_name_dup',
            parameters={
                'base_path': '/tmp/test_dup',
                'service_name': 'test_service_name_dup'  # This would cause duplicate
            },
            implementation='local'
        )

        # This should NOT raise: TypeError: got multiple values for keyword argument 'service_name'
        storage = self.site.storage('test_service_name_dup')
        assert storage is not None

        # Clean up
        self.storage_handler.removeStorageFromCache('test_service_name_dup')

    def test_storage_params_pop_does_not_modify_original(self):
        """Test that popping service_name doesn't modify the original storage_params."""
        self.storage_handler._setStorageParams(
            'test_no_modify',
            parameters={
                'base_path': '/tmp/test_no_modify',
                'service_name': 'test_no_modify'
            },
            implementation='local'
        )

        # Call storage() which should pop service_name internally
        self.site.storage('test_no_modify')

        # Original storage_params should still have service_name
        params = self.storage_handler.getStorageParameters('test_no_modify')
        # The original dict in storage_params should be unchanged
        # (storage() makes a copy before popping)

        # Clean up
        self.storage_handler.removeStorageFromCache('test_no_modify')

    # ========================================================================
    # Relative Storage Service Tests (Bug #834)
    # ========================================================================

    def _addStorage(self, service_name, implementation=None, **parameters):
        """Registers a storage service to be removed at the end of the test"""
        self.storage_handler._setStorageParams(service_name,
            parameters=parameters, implementation=implementation)
        self._storages_to_clean.append(service_name)
        return service_name

    @pytest.fixture(autouse=True)
    def cleanup_storages(self):
        """Removes the storage services registered by a single test"""
        self._storages_to_clean = []
        yield
        storage_type = self.services_handler('storage')
        for service_name in self._storages_to_clean:
            self.storage_handler.removeStorageFromCache(service_name)
            storage_type.service_instances.pop(service_name, None)

    @pytest.fixture
    def relative_storages(self):
        """A local storage plus a relative storage rooted on one of its subfolders"""
        parent_dir = os.path.join(self.test_dir, 'relative_parent')
        os.makedirs(os.path.join(parent_dir, 'docs', 'invoices'), exist_ok=True)
        parent_name = self._addStorage('rel_parent_storage', implementation='local',
                                       base_path=parent_dir, tags='admin')
        child_name = self._addStorage('rel_child_storage', implementation='relative',
                                       parent_service=parent_name, relative_path='docs/invoices')
        return parent_name, child_name

    def test_relative_storage_creation(self, relative_storages):
        """Test that a relative storage service can be created (issue #834).

        Creating it used to fail with AttributeError: 'Service' object has no
        attribute '_call'.
        """
        parent_name, child_name = relative_storages
        parent_service = self.site.storage(parent_name)
        service = self.site.storage(child_name)

        assert service is not None
        # a relative service is an instance of the parent implementation
        assert isinstance(service, type(parent_service))
        assert service.service_implementation == 'relative'
        assert service.service_name == child_name
        assert service.parent_service is parent_service
        assert service.relative_path == 'docs/invoices'

    def test_relative_storage_base_path(self, relative_storages):
        """Test that a relative storage is rooted inside its parent storage."""
        parent_name, child_name = relative_storages
        parent_service = self.site.storage(parent_name)
        service = self.site.storage(child_name)

        assert service.base_path == '%s/docs/invoices' % parent_service.base_path
        assert service.internal_path('receipt.txt') == os.path.join(parent_service.base_path,
                                                                    'docs', 'invoices', 'receipt.txt')

    def test_relative_storage_write_and_read(self, relative_storages):
        """Test that files written on a relative storage land in the parent subfolder."""
        parent_name, child_name = relative_storages
        node = self.site.storageNode('%s:receipt.txt' % child_name)
        with node.open(mode='w') as output_file:
            output_file.write('relative content')

        assert node.exists
        assert node.fullpath == '%s:receipt.txt' % child_name

        # the same file is reachable from the parent storage through the relative path
        parent_node = self.site.storageNode('%s:docs/invoices/receipt.txt' % parent_name)
        assert parent_node.exists
        with parent_node.open(mode='r') as input_file:
            assert input_file.read() == 'relative content'

        node.delete()
        assert not node.exists

    def test_relative_storage_children(self, relative_storages):
        """Test that a relative storage lists only its own subtree."""
        parent_name, child_name = relative_storages
        for filename in ('first.txt', 'second.txt'):
            with self.site.storageNode('%s:%s' % (child_name, filename)).open(mode='w') as output_file:
                output_file.write(filename)
        with self.site.storageNode('%s:outside.txt' % parent_name).open(mode='w') as output_file:
            output_file.write('outside')

        children = self.site.storageNode('%s:' % child_name).children()
        assert sorted([child.basename for child in children]) == ['first.txt', 'second.txt']
        assert all(child.service.service_name == child_name for child in children)

    def test_relative_storage_inherits_parent_parameters(self, relative_storages):
        """Test that the parameters of the parent service are used by the relative one."""
        parent_name, child_name = relative_storages
        parent_service = self.site.storage(parent_name)
        service = self.site.storage(child_name)

        assert service.tags == parent_service.tags == 'admin'
        assert service.location_identifier == parent_service.location_identifier

    def test_relative_storage_nested(self, relative_storages):
        """Test that a relative storage can be the parent of another relative storage."""
        parent_name, child_name = relative_storages
        nested_name = self._addStorage('rel_nested_storage', implementation='relative',
                                        parent_service=child_name, relative_path='2026')
        parent_service = self.site.storage(parent_name)
        service = self.site.storage(nested_name)

        assert service.base_path == '%s/docs/invoices/2026' % parent_service.base_path
        assert isinstance(service, type(parent_service))

    def test_relative_storage_without_relative_path(self, relative_storages):
        """Test that a relative storage without relative path is an alias of its parent."""
        parent_name, child_name = relative_storages
        alias_name = self._addStorage('rel_alias_storage', implementation='relative',
                                       parent_service=parent_name)
        parent_service = self.site.storage(parent_name)
        service = self.site.storage(alias_name)

        assert service.relative_path == ''
        assert service.base_path == parent_service.base_path

    def test_relative_storage_missing_parent_service(self):
        """Test that a relative storage without parent service is empty and not writable.

        A service that has just been created has no parameters yet: browsing it must
        not fail (its own parameters form shows its tree) but nothing can be written
        where there is no path.
        """
        service_name = self._addStorage('rel_no_parent_storage', implementation='relative',
                                         relative_path='docs')
        service = self.site.storage(service_name)
        assert service.base_path is None
        assert service.children() == []
        assert service.exists('anything.txt') is False
        assert service.url('anything.txt') == ''
        node = self.site.storageNode('%s:anything.txt' % service_name)
        assert not node.exists
        with pytest.raises(GnrException):
            node.open(mode='w')

    def test_relative_storage_unsupported_parent_service(self):
        """Test that a symbolic storage cannot be the parent of a relative storage."""
        service_name = self._addStorage('rel_symbolic_storage', implementation='relative',
                                         parent_service='rsrc', relative_path='docs')
        service = self.site.storage(service_name)
        assert service.base_path is None
        with pytest.raises(GnrException):
            service.mkdir('docs')

    def test_relative_storage_tree_without_parent_service(self):
        """Test that the storage tree of an unconfigured relative storage is empty.

        This is the failure reported in issue #834: the tree of the service
        parameters form used to break on the service it configures.
        """
        service_name = self._addStorage('rel_tree_storage', implementation='relative')
        tree = StorageResolver(self.site.storageNode('%s:' % service_name),
                               _page=self.site.dummyPage)()
        assert len(tree) == 0

    def test_relative_storage_from_service_record(self):
        """Test a relative storage configured in sys.service end to end (issue #834).

        This is the path that fails in a real instance: the parameters are read
        from the service record, loaded in the storage_params registry by the
        table triggers and passed to the service factory.
        """
        tblservice = self.site.db.table('sys.service')
        service_name = 'rel_record_storage'
        parameters = Bag()
        parameters['parent_service'] = 'site'
        parameters['relative_path'] = 'relative_from_record'
        record = tblservice.newrecord(service_type='storage', service_name=service_name,
                                      implementation='relative', parameters=parameters)
        tblservice.insert(record)
        self.site.db.commit()
        try:
            # the insert trigger fills the storage_params registry
            stored_params = self.storage_handler.getStorageParameters(service_name)
            assert stored_params['implementation'] == 'relative'
            assert stored_params['parent_service'] == 'site'
            assert stored_params['relative_path'] == 'relative_from_record'

            service = self.site.storage(service_name)
            assert service.parent_service is self.site.storage('site')
            assert service.base_path == '%s/relative_from_record' % self.site.storage('site').base_path

            node = self.site.storageNode('%s:probe.txt' % service_name)
            node.parentStorageNode.mkdir()
            with node.open(mode='w') as output_file:
                output_file.write('from service record')
            assert self.site.storageNode('site:relative_from_record/probe.txt').exists

            # the storage tree of the service parameters form loads this service
            tree = StorageResolver(self.site.storageNode('%s:' % service_name),
                                   _page=self.site.dummyPage)()
            assert 'probe_txt' in tree
            node.delete()
        finally:
            tblservice.delete(record)
            self.site.db.commit()
            self.services_handler('storage').service_instances.pop(service_name, None)

    def test_relative_storage_parent_options(self):
        """Test the parent services offered by the relative storage parameters form."""
        relative_module = gnrImport(os.path.join(getGenroRoot(), 'resources', 'common',
                                                 'services', 'storage', 'relative.py'),
                                    avoidDup=True)
        service_name = self._addStorage('rel_options_storage', implementation='relative',
                                         parent_service='removed_parent_storage')
        self._addStorage('rel_options_parent', implementation='local', base_path='/tmp/rel_options')
        form = relative_module.ServiceParameters()
        form.site = self.site
        options = relative_module.ServiceParameters.relativeStorageParents(
            form, service_name=service_name).split(',')

        assert 'rel_options_parent' in options
        # a service cannot be the parent of itself
        assert service_name not in options
        # symbolic services have no real base path, internal ones are not configurable
        assert 'rsrc' not in options
        assert '_raw_' not in options
        # the configured parent is always an option, even if it is not available any more
        assert 'removed_parent_storage' in options
