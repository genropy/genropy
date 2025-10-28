"""
Test suite for genro-storage wrapper compatibility

This test suite verifies that GenroStorageNodeWrapper provides
full backward compatibility with Genropy's native StorageNode API.

It reuses the same test cases from gnrstorage_test.py but with
the genro-storage wrapper instead of native implementation.
"""

import pytest
import os
import tempfile
import shutil

from gnr.lib.services.storage_genro_adapter import (
    GenroStorageNodeWrapper,
    GenroStorageConfigConverter,
    GenroStorageServiceAdapter,
    GENRO_STORAGE_AVAILABLE,
    GenroStorageManager
)


# Skip all tests if genro-storage is not available
pytestmark = pytest.mark.skipif(
    not GENRO_STORAGE_AVAILABLE,
    reason="genro-storage not installed"
)


class MockStorageManager:
    """Mock storage manager using genro-storage"""
    def __init__(self, base_path):
        self.base_path = base_path
        self.external_host = 'http://localhost:8080'
        self.cache_max_age = 3600

        # Initialize genro-storage
        self._genro_storage = GenroStorageManager()
        self._genro_storage.configure([{
            'name': 'test',
            'type': 'local',
            'path': base_path
        }])

    def storageNode(self, path):
        """Parse path and return wrapped GenroStorageNode"""
        if ':' in path:
            service_name, node_path = path.split(':', 1)
        else:
            service_name = 'test'
            node_path = path

        # Get genro-storage node
        full_path = f'{service_name}:{node_path}'
        genro_node = self._genro_storage.node(full_path)

        # Create mock service for wrapper
        service = GenroStorageServiceAdapter(
            parent=self,
            storage_manager=self._genro_storage,
            mount_name=service_name
        )

        # Wrap it with Genropy API
        return GenroStorageNodeWrapper(genro_node, parent=self, service=service)

    def not_found_exception(self, environ, start_response):
        start_response('404 Not Found', [])
        return [b'Not Found']


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing"""
    temp_dir = tempfile.mkdtemp()
    manager = MockStorageManager(temp_dir)

    yield manager

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestStorageNodeProperties:
    """Test StorageNode properties with genro-storage wrapper"""

    def test_fullpath(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert node.fullpath == 'test:path/to/file.txt'

    def test_basename(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert node.basename == 'file.txt'

    def test_cleanbasename(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert node.cleanbasename == 'file'

    def test_ext(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert node.ext == 'txt'

    def test_ext_no_extension(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file')
        assert node.ext == ''

    def test_splitext(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        name, ext = node.splitext()
        assert ext == '.txt'

    def test_dirname(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        dirname = node.dirname
        assert dirname is not None
        assert 'path/to' in dirname

    def test_internal_path(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert 'path/to/file.txt' in node.internal_path


class TestStorageNodeFileOperations:
    """Test file read/write operations"""

    def test_exists_false(self, temp_storage):
        node = temp_storage.storageNode('test:nonexistent.txt')
        assert node.exists is False

    def test_exists_true(self, temp_storage):
        node = temp_storage.storageNode('test:existing.txt')
        with node.open('wb') as f:
            f.write(b'content')
        assert node.exists is True

    def test_isfile_true(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'content')
        assert node.isfile is True
        assert node.isdir is False

    def test_isdir_true(self, temp_storage):
        node = temp_storage.storageNode('test:mydir')
        node.mkdir()
        assert node.isdir is True
        assert node.isfile is False

    def test_open_write_read(self, temp_storage):
        node = temp_storage.storageNode('test:data.txt')

        # Write
        with node.open('w') as f:
            f.write('Hello World')

        # Read
        with node.open('r') as f:
            content = f.read()

        assert content == 'Hello World'

    def test_open_binary(self, temp_storage):
        node = temp_storage.storageNode('test:data.bin')

        data = b'\x00\x01\x02\x03'
        with node.open('wb') as f:
            f.write(data)

        with node.open('rb') as f:
            read_data = f.read()

        assert read_data == data

    def test_size(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        content = b'Hello World'
        with node.open('wb') as f:
            f.write(content)

        assert node.size == len(content)

    def test_mtime(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'content')

        mtime = node.mtime
        assert isinstance(mtime, (int, float))
        assert mtime > 0

    def test_ext_attributes(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'content')

        mtime, size, isdir = node.ext_attributes
        assert isinstance(mtime, (int, float))
        assert size == 7
        assert isdir is False


class TestStorageNodeDirectoryOperations:
    """Test directory operations"""

    def test_mkdir(self, temp_storage):
        node = temp_storage.storageNode('test:newdir')
        assert not node.exists

        node.mkdir()
        assert node.exists
        assert node.isdir

    def test_child(self, temp_storage):
        parent = temp_storage.storageNode('test:parent')
        parent.mkdir()

        child = parent.child('child.txt')
        assert child.basename == 'child.txt'
        assert 'parent' in child.fullpath

    def test_children_empty(self, temp_storage):
        node = temp_storage.storageNode('test:emptydir')
        node.mkdir()

        children = node.children()
        assert children == []

    def test_children_with_files(self, temp_storage):
        parent = temp_storage.storageNode('test:parent')
        parent.mkdir()

        # Create some files
        for i in range(3):
            child = parent.child(f'file{i}.txt')
            with child.open('w') as f:
                f.write(f'content {i}')

        children = parent.children()
        assert len(children) == 3
        assert all(isinstance(c, GenroStorageNodeWrapper) for c in children)


class TestStorageNodeCopyMove:
    """Test copy and move operations"""

    def test_copy_file(self, temp_storage):
        source = temp_storage.storageNode('test:source.txt')
        with source.open('w') as f:
            f.write('Hello World')

        dest = temp_storage.storageNode('test:dest.txt')
        source.copy(dest)

        assert dest.exists
        with dest.open('r') as f:
            assert f.read() == 'Hello World'

    def test_delete_file(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        assert node.exists
        node.delete()
        assert not node.exists


class TestStorageNodeUtilities:
    """Test utility methods"""

    def test_md5hash(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'Hello World')

        hash_value = node.md5hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hex digest

    def test_mimetype(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        mimetype = node.mimetype
        assert 'text' in mimetype or mimetype == 'application/octet-stream'

    def test_base64_no_mime(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'Hello')

        b64 = node.base64(mime=False)
        assert isinstance(b64, str)
        # Should be base64 encoded
        import base64
        decoded = base64.b64decode(b64)
        assert decoded == b'Hello'

    def test_base64_with_mime(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'Hello')

        b64 = node.base64(mime=True)
        assert b64.startswith('data:')
        assert 'base64,' in b64


class TestStorageNodeContextManager:
    """Test local_path context manager"""

    def test_local_path_read(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('Hello World')

        with node.local_path(mode='r') as local_path:
            assert os.path.exists(local_path)
            with open(local_path, 'r') as f:
                content = f.read()
            assert content == 'Hello World'


class TestConfigConverter:
    """Test configuration converter"""

    def test_convert_local(self):
        genropy_config = {
            'name': 'uploads',
            'implementation': 'local',
            'base_path': '/tmp/uploads'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['name'] == 'uploads'
        assert result['type'] == 'local'
        assert result['path'] == '/tmp/uploads'

    def test_convert_s3(self):
        genropy_config = {
            'name': 's3storage',
            'implementation': 's3',
            'bucket': 'my-bucket',
            'region': 'us-east-1'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['name'] == 's3storage'
        assert result['type'] == 's3'
        assert result['bucket'] == 'my-bucket'
        assert result['region'] == 'us-east-1'

    def test_convert_symbolic(self):
        # Symbolic should map to local
        genropy_config = {
            'name': 'temp',
            'implementation': 'symbolic'
        }

        result = GenroStorageConfigConverter.convert(genropy_config)

        assert result['type'] == 'local'

    def test_convert_multiple(self):
        configs = [
            {'name': 'local1', 'implementation': 'local', 'base_path': '/tmp'},
            {'name': 's3_1', 'implementation': 's3', 'bucket': 'bucket1'}
        ]

        results = GenroStorageConfigConverter.convert_multiple(configs)

        assert len(results) == 2
        assert results[0]['type'] == 'local'
        assert results[1]['type'] == 's3'
