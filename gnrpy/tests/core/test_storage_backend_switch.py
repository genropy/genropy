"""
Test suite for storage backend switch functionality

Tests the runtime switch between native and genro-storage backends,
including configuration, initialization, and integration with site.storageNode
"""

import pytest
from unittest.mock import Mock

from gnr.core.gnrbag import Bag
from gnr.lib.services.storage_genro_adapter import (
    should_use_genro_storage,
    get_storage_backend_preference,
    GenroStorageConfigConverter,
    GENRO_STORAGE_AVAILABLE
)


class TestBackendSwitch:
    """Test backend selection logic"""

    def test_default_to_native(self):
        """Should default to native when no config specified"""
        mock_site = Mock()
        mock_site.config = Bag()

        backend = get_storage_backend_preference(mock_site)
        assert backend == 'native'

    def test_explicit_native_config(self):
        """Should use native when explicitly configured"""
        mock_site = Mock()
        mock_site.config = Bag()
        mock_site.config['storage_backend'] = 'native'

        backend = get_storage_backend_preference(mock_site)
        assert backend == 'native'
        assert not should_use_genro_storage(mock_site)

    def test_genro_storage_config(self):
        """Should use genro-storage when configured"""
        mock_site = Mock()
        mock_site.config = Bag()
        mock_site.config['storage_backend'] = 'genro-storage'

        backend = get_storage_backend_preference(mock_site)
        assert backend == 'genro-storage'

        # Only returns True if genro-storage is actually available
        result = should_use_genro_storage(mock_site)
        if GENRO_STORAGE_AVAILABLE:
            assert result is True
        else:
            assert result is False

    def test_invalid_backend_defaults_to_native(self):
        """Invalid backend config should default to native"""
        mock_site = Mock()
        mock_site.config = Bag()
        mock_site.config['storage_backend'] = 'invalid-backend'

        backend = get_storage_backend_preference(mock_site)
        assert backend == 'native'


class TestConfigConverter:
    """Test Genropy to genro-storage config conversion"""

    def test_convert_local_implementation(self):
        """Convert local implementation config"""
        genropy_config = {
            'name': 'uploads',
            'implementation': 'local',
            'base_path': '/tmp/uploads'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['name'] == 'uploads'
        assert result['type'] == 'local'
        assert result['path'] == '/tmp/uploads'
        assert 'implementation' not in result
        assert 'base_path' not in result

    def test_convert_s3_implementation(self):
        """Convert S3 implementation config"""
        genropy_config = {
            'name': 's3storage',
            'implementation': 's3',
            'bucket': 'my-bucket',
            'region': 'us-east-1',
            'access_key': 'KEY',
            'secret_key': 'SECRET'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['name'] == 's3storage'
        assert result['type'] == 's3'
        assert result['bucket'] == 'my-bucket'
        assert result['region'] == 'us-east-1'
        assert result['access_key'] == 'KEY'
        assert result['secret_key'] == 'SECRET'

    def test_convert_symbolic_to_local(self):
        """Symbolic implementation should map to local"""
        genropy_config = {
            'name': 'temp',
            'implementation': 'symbolic'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['type'] == 'local'

    def test_convert_raw_to_local(self):
        """Raw implementation should map to local"""
        genropy_config = {
            'name': 'raw',
            'implementation': 'raw'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['type'] == 'local'

    def test_convert_multiple_configs(self):
        """Convert multiple service configs at once"""
        configs = [
            {'name': 'local1', 'implementation': 'local', 'base_path': '/tmp'},
            {'name': 's3_1', 'implementation': 's3', 'bucket': 'bucket1'},
            {'name': 'gcs_1', 'implementation': 'gcs', 'bucket': 'bucket2'}
        ]

        results = GenroStorageConfigConverter.convert_multiple(configs)

        assert len(results) == 3
        assert results[0]['type'] == 'local'
        assert results[1]['type'] == 's3'
        assert results[2]['type'] == 'gcs'

    def test_convert_preserves_extra_params(self):
        """Extra parameters should be preserved"""
        genropy_config = {
            'name': 'test',
            'implementation': 's3',
            'bucket': 'test-bucket',
            'custom_param': 'value',
            'another_param': 123
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['custom_param'] == 'value'
        assert result['another_param'] == 123

    def test_convert_filters_internal_keys(self):
        """Internal keys should be filtered out"""
        genropy_config = {
            'name': 'test',
            'implementation': 'local',
            'base_path': '/tmp',
            'service_type': 'storage',  # Should be filtered
            'service_name': 'test'      # Should be filtered
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert 'service_type' not in result
        assert 'service_name' not in result


@pytest.mark.skipif(
    not GENRO_STORAGE_AVAILABLE,
    reason="genro-storage not installed"
)
class TestGenroStorageIntegration:
    """Test integration with genro-storage when available"""

    def test_can_import_genro_storage(self):
        """Should be able to import genro-storage components"""
        from gnr.lib.services.storage_genro_adapter import (
            GenroStorageManager,
            GenroStorageNodeWrapper,
            GenroStorageServiceAdapter
        )

        assert GenroStorageManager is not None
        assert GenroStorageNodeWrapper is not None
        assert GenroStorageServiceAdapter is not None

    def test_genro_storage_manager_initialization(self):
        """Should be able to initialize GenroStorageManager"""
        from gnr.lib.services.storage_genro_adapter import GenroStorageManager

        manager = GenroStorageManager()
        assert manager is not None

    def test_genro_storage_manager_configuration(self):
        """Should be able to configure mount points"""
        import tempfile
        from gnr.lib.services.storage_genro_adapter import GenroStorageManager

        temp_dir = tempfile.mkdtemp()
        manager = GenroStorageManager()

        config = [{
            'name': 'test',
            'type': 'local',
            'path': temp_dir
        }]

        manager.configure(config)
        # If no exception, configuration succeeded

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestStorageNodeImports:
    """Test that storageNode can handle both node types"""

    def test_can_import_storage_node(self):
        """Should be able to import native StorageNode"""
        from gnr.lib.services.storage import StorageNode

        assert StorageNode is not None

    @pytest.mark.skipif(
        not GENRO_STORAGE_AVAILABLE,
        reason="genro-storage not installed"
    )
    def test_can_import_wrapper_node(self):
        """Should be able to import GenroStorageNodeWrapper when available"""
        from gnr.lib.services.storage_genro_adapter import GenroStorageNodeWrapper

        assert GenroStorageNodeWrapper is not None
