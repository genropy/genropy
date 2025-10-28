"""
Test suite for Genropy StorageNode API

This test suite documents and verifies the current behavior of StorageNode.
It will be used to ensure backward compatibility when integrating genro-storage.
"""

import pytest
import os
import tempfile
import shutil
from gnr.lib.services.storage import StorageNode, BaseLocalService, NotExistingStorageNode


class MockStorageManager:
    """Mock storage manager for testing"""
    def __init__(self, base_path):
        self.base_path = base_path
        self.external_host = 'http://localhost:8080'
        self.cache_max_age = 3600

    def storageNode(self, path):
        """Parse path and return StorageNode"""
        if ':' in path:
            service_name, node_path = path.split(':', 1)
        else:
            service_name = 'test'
            node_path = path

        service = BaseLocalService(parent=self, base_path=self.base_path)
        service.service_name = service_name
        service.service_implementation = 'local'

        return StorageNode(parent=self, path=node_path, service=service)

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
    """Test StorageNode properties"""

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
        assert node.dirname == 'test:path/to'

    def test_internal_path(self, temp_storage):
        node = temp_storage.storageNode('test:path/to/file.txt')
        assert node.internal_path.endswith('path/to/file.txt')


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
        assert isinstance(mtime, float)
        assert mtime > 0

    def test_ext_attributes(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('wb') as f:
            f.write(b'content')

        mtime, size, isdir = node.ext_attributes
        assert isinstance(mtime, float)
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

    def test_mkdir_exists(self, temp_storage):
        node = temp_storage.storageNode('test:existingdir')
        node.mkdir()
        # Should not raise error
        node.mkdir()

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
        assert all(isinstance(c, StorageNode) for c in children)

    def test_listdir(self, temp_storage):
        parent = temp_storage.storageNode('test:parent')
        parent.mkdir()

        # Create files
        for i in range(2):
            child = parent.child(f'file{i}.txt')
            with child.open('w') as f:
                f.write(f'content {i}')

        paths = parent.listdir()
        assert len(paths) == 2
        assert all(':' in p for p in paths)  # Should be fullpaths

    def test_parentStorageNode(self, temp_storage):
        node = temp_storage.storageNode('test:parent/child/file.txt')
        parent_node = node.parentStorageNode

        assert isinstance(parent_node, StorageNode)
        assert parent_node.basename == 'child'


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

    def test_copy_to_directory(self, temp_storage):
        source = temp_storage.storageNode('test:source.txt')
        with source.open('w') as f:
            f.write('content')

        dest_dir = temp_storage.storageNode('test:destdir')
        dest_dir.mkdir()

        source.copy(dest_dir)

        # Should copy with same basename
        copied = dest_dir.child('source.txt')
        assert copied.exists

    def test_move_file(self, temp_storage):
        source = temp_storage.storageNode('test:source.txt')
        with source.open('w') as f:
            f.write('Hello World')

        dest = temp_storage.storageNode('test:dest.txt')
        source.move(dest)

        # Source path should update
        assert source.path == dest.path
        assert dest.exists

    def test_delete_file(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        assert node.exists
        node.delete()
        assert not node.exists

    def test_delete_directory(self, temp_storage):
        node = temp_storage.storageNode('test:mydir')
        node.mkdir()

        # Add a file
        child = node.child('file.txt')
        with child.open('w') as f:
            f.write('content')

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
        assert 'text' in node.mimetype

        node_pdf = temp_storage.storageNode('test:file.pdf')
        assert 'pdf' in node_pdf.mimetype

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

    def test_url(self, temp_storage):
        node = temp_storage.storageNode('test:path/file.txt')
        url = node.url()

        assert isinstance(url, str)
        assert 'test' in url  # service name

    def test_internal_url(self, temp_storage):
        node = temp_storage.storageNode('test:path/file.txt')
        url = node.internal_url()

        assert isinstance(url, str)
        assert '_storage' in url
        assert 'test' in url

    def test_internal_url_nocache(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        url = node.internal_url(nocache=True)
        assert 'mtime=' in url

    def test_fill_from_url(self, temp_storage):
        # This would need mocking of urllib
        # Skipping for now - integration test
        pass


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

    def test_local_path_write(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')

        with node.local_path(mode='w') as local_path:
            with open(local_path, 'w') as f:
                f.write('New Content')

        # Content should be persisted
        with node.open('r') as f:
            assert f.read() == 'New Content'


class TestStorageNodeMetadata:
    """Test metadata operations (if supported by backend)"""

    def test_get_metadata_not_implemented(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        # BaseLocalService doesn't implement metadata - should raise AttributeError
        with pytest.raises(AttributeError):
            node.get_metadata()

    def test_set_metadata_not_implemented(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        # BaseLocalService doesn't implement metadata - should raise AttributeError
        with pytest.raises(AttributeError):
            node.set_metadata({'key': 'value'})


class TestStorageNodeExceptions:
    """Test error handling"""

    def test_must_exist_raises(self, temp_storage):
        with pytest.raises(NotExistingStorageNode):
            temp_storage.storageNode('test:nonexistent.txt').service.parent.storageNode(
                'test:nonexistent.txt'
            )
            # Need to create with must_exist=True
            StorageNode(
                parent=temp_storage,
                path='nonexistent.txt',
                service=temp_storage.storageNode('test:').service,
                must_exist=True
            )


class TestStorageNodeEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_directory_children(self, temp_storage):
        node = temp_storage.storageNode('test:emptydir')
        node.mkdir()

        children = node.children()
        assert children is not None
        assert len(children) == 0

    def test_file_children_returns_none(self, temp_storage):
        node = temp_storage.storageNode('test:file.txt')
        with node.open('w') as f:
            f.write('content')

        # children() should return None for files
        children = node.children()
        assert children is None

    def test_path_with_trailing_slash(self, temp_storage):
        node = temp_storage.storageNode('test:mydir/')
        node.mkdir()

        child = node.child('file.txt')
        # Should handle trailing slash correctly
        assert 'file.txt' in child.fullpath

    def test_path_normalization(self, temp_storage):
        node = temp_storage.storageNode('test:path//to///file.txt')
        # Should handle multiple slashes
        assert node.basename == 'file.txt'
