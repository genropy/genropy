"""
Adapter between Genropy storage system and genro-storage library

This module provides:
1. Configuration converter: Genropy config → genro-storage config
2. StorageNode wrapper: genro-storage API → Genropy API compatibility
3. Runtime switch: native vs genro-storage backend

Usage:
    # In site configuration
    STORAGE_BACKEND = 'genro-storage'  # or 'native'

    # Or per-service override
    storage.configure([
        {'name': 'uploads', 'type': 's3', 'backend': 'genro-storage'},
        {'name': 'legacy', 'type': 'local', 'backend': 'native'}
    ])
"""

import os
from gnr.lib.services.storage import StorageNode as NativeStorageNode
from gnr.lib.services.storage import StorageService, BaseLocalService

# Try to import genro-storage
try:
    from genro_storage import StorageManager as GenroStorageManager
    GENRO_STORAGE_AVAILABLE = True
except ImportError:
    GENRO_STORAGE_AVAILABLE = False
    GenroStorageManager = None

# Export for external use
__all__ = [
    'GenroStorageManager',
    'GENRO_STORAGE_AVAILABLE',
    'GenroStorageConfigConverter',
    'GenroStorageNodeWrapper',
    'GenroStorageServiceAdapter',
    'get_storage_backend_preference',
    'should_use_genro_storage'
]


class GenroStorageConfigConverter:
    """
    Converts Genropy storage configuration to genro-storage format

    Genropy format:
        {
            'name': 'uploads',
            'implementation': 'local',  # or 's3', 'gcs', etc.
            'base_path': '/path/to/storage',
            'bucket': 'my-bucket',  # for S3
            'region': 'us-east-1',  # for S3
            ...
        }

    genro-storage format:
        {
            'name': 'uploads',
            'type': 'local',  # or 's3', 'gcs', etc.
            'path': '/path/to/storage',  # for local
            'bucket': 'my-bucket',  # for S3
            'region': 'us-east-1',  # for S3
            ...
        }
    """

    # Mapping from Genropy implementation names to genro-storage types
    IMPLEMENTATION_MAP = {
        'local': 'local',
        'symbolic': 'local',  # Genropy symbolic is like local
        'raw': 'local',       # Genropy raw is like local
        's3': 's3',
        'gcs': 'gcs',
        'azure': 'azure',
        'http': 'http',
        'https': 'http',
    }

    # Parameter name mappings
    PARAM_MAP = {
        'base_path': 'path',
        'implementation': 'type',
    }

    @classmethod
    def convert(cls, genropy_config):
        """
        Convert a single Genropy service config to genro-storage format

        Args:
            genropy_config (dict): Genropy service configuration

        Returns:
            dict: genro-storage mount configuration
        """
        if not genropy_config:
            return None

        result = {}

        # Convert implementation to type
        implementation = genropy_config.get('implementation', 'local')
        result['type'] = cls.IMPLEMENTATION_MAP.get(implementation, implementation)

        # Copy service name
        if 'name' in genropy_config:
            result['name'] = genropy_config['name']

        # Convert parameters
        for genropy_key, value in genropy_config.items():
            if genropy_key in ('implementation', 'name', 'service_type', 'service_name'):
                continue

            # Map parameter name
            genro_key = cls.PARAM_MAP.get(genropy_key, genropy_key)
            result[genro_key] = value

        return result

    @classmethod
    def convert_multiple(cls, genropy_configs):
        """
        Convert multiple Genropy service configs to genro-storage format

        Args:
            genropy_configs (list): List of Genropy service configurations

        Returns:
            list: List of genro-storage mount configurations
        """
        return [cls.convert(config) for config in genropy_configs if config]


class GenroStorageNodeWrapper:
    """
    Wrapper around genro-storage StorageNode that provides Genropy API compatibility

    This wrapper delegates to a genro-storage StorageNode but exposes the
    Genropy StorageNode API (properties and methods).
    """

    def __init__(self, genro_node, parent=None, service=None):
        """
        Initialize wrapper

        Args:
            genro_node: genro-storage StorageNode instance
            parent: Genropy parent (site)
            service: Genropy StorageService instance
        """
        self._genro_node = genro_node
        self._parent = parent
        self._service = service

    # Properties - direct mapping

    @property
    def fullpath(self):
        """Returns the full symbolic path (eg. storage:path/to/me)"""
        return self._genro_node.fullpath

    @property
    def basename(self):
        """Returns the base name (eg. self.path=="/path/to/me.txt" self.basename=="me.txt")"""
        return self._genro_node.basename

    @property
    def cleanbasename(self):
        """Returns the basename without extension"""
        return self._genro_node.stem  # genro-storage uses 'stem'

    @property
    def ext(self):
        """Returns the file extension without leading dots"""
        suffix = self._genro_node.suffix
        return suffix.lstrip('.') if suffix else ''

    @property
    def isdir(self):
        """Returns True if the StorageNode points to a directory"""
        return self._genro_node.isdir

    @property
    def isfile(self):
        """Returns True if the StorageNode points to a file"""
        return self._genro_node.isfile

    @property
    def exists(self):
        """Returns True if the StorageNode points to an existing file/dir"""
        return self._genro_node.exists

    @property
    def mtime(self):
        """Returns the last modification timestamp"""
        return self._genro_node.mtime

    @property
    def size(self):
        """Returns the file size (if self.isfile)"""
        return self._genro_node.size

    @property
    def md5hash(self):
        """Returns the md5 hash"""
        return self._genro_node.md5hash

    @property
    def mimetype(self):
        """Returns the file mime type"""
        return self._genro_node.mimetype

    @property
    def dirname(self):
        """Returns the fullpath of parent directory"""
        parent = self._genro_node.parent
        return parent.fullpath if parent else None

    @property
    def internal_path(self):
        """Returns the internal path (without mount prefix)"""
        return self._genro_node.path

    @property
    def path(self):
        """Returns the internal path (alias for internal_path)"""
        return self._genro_node.path

    @property
    def parentStorageNode(self):
        """Returns the StorageNode pointing to the parent directory"""
        parent = self._genro_node.parent
        if parent:
            return GenroStorageNodeWrapper(parent, self._parent, self._service)
        return None

    @property
    def ext_attributes(self):
        """Returns the file size (if self.isfile) - Genropy specific"""
        if not self.exists:
            return None, None, None
        return self.mtime, self.size, self.isdir

    @property
    def parent(self):
        """Returns the parent (site) - Genropy compatibility"""
        return self._parent

    @property
    def service(self):
        """Returns the service - Genropy compatibility"""
        return self._service

    # Methods

    def splitext(self):
        """Returns a tuple of filename and extension"""
        import os
        return os.path.splitext(self._genro_node.path)

    def open(self, mode='rb'):
        """Is a context manager that returns the open file pointed"""
        return self._genro_node.open(mode=mode)

    def mkdir(self, parents=False, exist_ok=True):
        """Creates me as a directory"""
        return self._genro_node.mkdir(parents=parents, exist_ok=exist_ok)

    def children(self):
        """Returns a list of StorageNodes contained (if self.isdir)"""
        if not self.isdir:
            return None

        genro_children = self._genro_node.children()
        if not genro_children:
            return []

        return [GenroStorageNodeWrapper(child, self._parent, self._service)
                for child in genro_children]

    def listdir(self):
        """Returns a list of file/dir names contained (if self.isdir)"""
        children = self.children()
        return [child.fullpath for child in children] if children else []

    def child(self, path=None):
        """Returns a StorageNode pointing a sub path"""
        child_node = self._genro_node.child(path)
        return GenroStorageNodeWrapper(child_node, self._parent, self._service)

    def delete(self):
        """Deletes the dir content"""
        return self._genro_node.delete()

    def copy(self, dest=None):
        """Copy self to another path"""
        # dest can be a string path or a StorageNode
        if isinstance(dest, (GenroStorageNodeWrapper, NativeStorageNode)):
            dest_path = dest.fullpath
        else:
            dest_path = dest

        # Parse destination
        dest_node = self._parent.storageNode(dest_path)

        # Perform copy
        self._genro_node.copy(dest_node._genro_node if isinstance(dest_node, GenroStorageNodeWrapper) else dest_path)

        return dest_node

    def move(self, dest=None):
        """Moves the pointed file to another path, self now points to the new location"""
        # Similar to copy but also updates self
        if isinstance(dest, (GenroStorageNodeWrapper, NativeStorageNode)):
            dest_path = dest.fullpath
        else:
            dest_path = dest

        dest_node = self._parent.storageNode(dest_path)

        # Perform move
        self._genro_node.move(dest_node._genro_node if isinstance(dest_node, GenroStorageNodeWrapper) else dest_path)

        # Update self to point to new location
        self._genro_node = dest_node._genro_node if isinstance(dest_node, GenroStorageNodeWrapper) else dest_node

        return dest_node

    def base64(self, mime=None):
        """Returns the base64 encoded string of the file content"""
        if mime:
            return self._genro_node.to_base64(mime_type=mime, data_uri=True)
        else:
            return self._genro_node.to_base64(mime_type=None, data_uri=False)

    def url(self, **kwargs):
        """Returns the external url of this file"""
        # genro-storage has url() for presigned URLs (S3)
        # Genropy uses url() for internal URLs typically
        # For now, delegate to internal_url
        return self.internal_url(**kwargs)

    def internal_url(self, **kwargs):
        """Returns the internal URL"""
        # genro-storage has internal_url() method
        nocache = kwargs.pop('nocache', None)
        return self._genro_node.internal_url(nocache=nocache)

    def local_path(self, mode=None, keep=False):
        """Is a context manager that return a local path to a temporary file"""
        return self._genro_node.local_path(mode=mode or 'r')

    def serve(self, environ, start_response, **kwargs):
        """Serves the file content"""
        return self._genro_node.serve(environ, start_response, **kwargs)

    def get_metadata(self):
        """Returns the file metadata"""
        if self._genro_node.capabilities.metadata:
            return self._genro_node.get_metadata()
        # Raise AttributeError for compatibility with Genropy tests
        raise AttributeError("'GenroStorageNodeWrapper' object has no attribute 'get_metadata'")

    def set_metadata(self, metadata):
        """Sets the file metadata"""
        if self._genro_node.capabilities.metadata:
            return self._genro_node.set_metadata(metadata)
        # Raise AttributeError for compatibility with Genropy tests
        raise AttributeError("'GenroStorageNodeWrapper' object has no attribute 'set_metadata'")

    def fill_from_url(self, url):
        """Downloads from URL and writes to node"""
        return self._genro_node.fill_from_url(url, timeout=30)

    def __str__(self):
        return f'GenroStorageNodeWrapper({self.fullpath})'


class GenroStorageServiceAdapter(StorageService):
    """
    Adapter that makes genro-storage act like a Genropy StorageService

    This allows genro-storage to be used as a drop-in replacement for
    Genropy's native storage service.
    """

    def __init__(self, parent=None, storage_manager=None, mount_name=None, **kwargs):
        """
        Initialize adapter

        Args:
            parent: Site instance
            storage_manager: GenroStorageManager instance
            mount_name: Name of the mount point
        """
        super().__init__(parent=parent, **kwargs)
        self._storage_manager = storage_manager
        self._mount_name = mount_name
        self.service_name = mount_name
        self.service_implementation = 'genro-storage'

    def _get_genro_node(self, *args):
        """Get genro-storage node from path components"""
        path = '/'.join(str(arg) for arg in args if arg)
        full_path = f'{self._mount_name}:{path}'
        return self._storage_manager.node(full_path)

    def expandpath(self, path):
        """Expand path (pass-through for genro-storage)"""
        return path

    def exists(self, *args):
        """Check if path exists"""
        node = self._get_genro_node(*args)
        return node.exists

    def isdir(self, *args):
        """Check if path is directory"""
        node = self._get_genro_node(*args)
        return node.isdir

    def isfile(self, *args):
        """Check if path is file"""
        node = self._get_genro_node(*args)
        return node.isfile

    def size(self, *args):
        """Get file size"""
        node = self._get_genro_node(*args)
        return node.size

    def mtime(self, *args):
        """Get modification time"""
        node = self._get_genro_node(*args)
        return node.mtime

    def md5hash(self, *args):
        """Get MD5 hash"""
        node = self._get_genro_node(*args)
        return node.md5hash

    def open(self, *args, **kwargs):
        """Open file"""
        node = self._get_genro_node(*args)
        return node.open(**kwargs)

    def mkdir(self, *args, **kwargs):
        """Create directory"""
        node = self._get_genro_node(*args)
        return node.mkdir(**kwargs)

    def delete(self, *args):
        """Delete file or directory"""
        node = self._get_genro_node(*args)
        return node.delete()

    def children(self, *args, **kwargs):
        """List children of directory"""
        node = self._get_genro_node(*args)
        if not node.isdir:
            return []

        children = node.children()
        # Wrap each child
        return [GenroStorageNodeWrapper(child, self.parent, self) for child in children]

    def basename(self, path=None):
        """Get basename of path"""
        import os
        return os.path.basename(path)

    def extension(self, path=None):
        """Get extension without dot"""
        import os
        ext = os.path.splitext(path)[1]
        return ext.lstrip('.')

    def internal_path(self, *args, **kwargs):
        """Get internal path"""
        return '/'.join(str(arg) for arg in args if arg)

    def fullpath(self, path):
        """Get full path with mount name"""
        return f"{self._mount_name}:{path}"

    def mimetype(self, *args, **kwargs):
        """Get MIME type"""
        node = self._get_genro_node(*args)
        return node.mimetype

    def ext_attributes(self, *args):
        """Get extended attributes (mtime, size, isdir)"""
        node = self._get_genro_node(*args)
        return node.mtime, node.size, node.isdir

    @property
    def location_identifier(self):
        """Return location identifier for copy optimization"""
        return f'genro-storage:{self._mount_name}'


def get_storage_backend_preference(site, service_name=None):
    """
    Determine which storage backend to use

    Priority:
    1. Per-service configuration
    2. Global site configuration
    3. Default (native)

    Args:
        site: Site instance
        service_name: Optional service name

    Returns:
        str: 'native' or 'genro-storage'
    """
    # Check if genro-storage is available
    if not GENRO_STORAGE_AVAILABLE:
        return 'native'

    # Check per-service override (if implemented in config)
    if service_name:
        service_backend = site.config.getAttr(f'services.{service_name}.backend')
        if service_backend:
            return service_backend

    # Check global default
    global_backend = site.config.get('storage_backend', 'native')

    return global_backend


def should_use_genro_storage(site, service_name=None):
    """
    Determine if genro-storage should be used

    Returns:
        bool: True if genro-storage should be used, False for native
    """
    backend = get_storage_backend_preference(site, service_name)
    return backend == 'genro-storage' and GENRO_STORAGE_AVAILABLE
