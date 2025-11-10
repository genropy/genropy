#!/usr/bin/env python
# encoding: utf-8
"""
Storage Handler Module

This module provides storage handling functionality for Genropy web applications.
It implements a proxy pattern to manage storage nodes and services, supporting both
legacy storage implementations and the new genro-storage library integration.

The module defines:
- BaseStorageHandler: Base class with core storage operations
- LegacyStorageHandler: Implementation using legacy gnr.lib.services.storage.StorageNode
- NewStorageNode: Wrapper providing LegacyStorageNode-compatible API for genro-storage BrickStorageNode
- NewStorageHandler: Implementation using genro-storage library (StorageManager + BrickStorageNode)
- LegacyStorageServiceAdapter: Minimal deprecated adapter for site.storage() backward compatibility

Integration with genro-storage:
    The NewStorageHandler uses the genro-storage library to provide a modern, unified
    storage abstraction across local filesystems, cloud storage (S3, GCS, Azure), and
    remote protocols (HTTP, SFTP, etc.).

Configuration:
    Storage handler selection will be configurable via siteconfig.xml:
    <storage_handler>new</storage_handler>  # Use genro-storage (NewStorageHandler)
    <storage_handler>legacy</storage_handler>  # Use legacy implementation (default)

Migration notes:
    - site.storage('name').method() pattern is deprecated when using NewStorageHandler
    - Use site.storageNode('name:path').method() directly instead
    - NewStorageNode provides full API compatibility with LegacyStorageNode
"""

import os
import logging
import random
from urllib.parse import urlencode

from gnr.lib.services.storage import StorageNode as LegacyStorageNode
from gnr.core.gnrsys import expandpath
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import deprecated

# Integration with genro-storage library
from genro_storage import StorageNode as BrickStorageNode
from genro_storage import StorageManager


class BaseStorageHandler:
    """Base class for storage handling.

    Provides core storage operations including service resolution, path adaptation,
    and storage node creation. Designed to be subclassed for specific implementations.

    Args:
        site: The GnrWsgiSite instance this handler belongs to
    """

    # Default configurations for built-in storage services
    DEFAULT_STORAGE_CONFIGS = {
        'user': {'implementation': 'symbolic'},
        'conn': {'implementation': 'symbolic'},
        'page': {'implementation': 'symbolic'},
        'temp': {'implementation': 'symbolic'},
        'rsrc': {'implementation': 'symbolic'},
        'pkg': {'implementation': 'symbolic'},
        'dojo': {'implementation': 'symbolic'},
        'gnr': {'implementation': 'symbolic'},
        'pages': {'implementation': 'symbolic'},
        '_raw_': {'implementation': 'raw'},
        '_http_': {'implementation': 'http'},
    }

    def __init__(self, site):
        """Initialize the storage handler.

        Args:
            site: The GnrWsgiSite instance
        """
        self.site = site
        self.storage_params = {}
        self._loadAllStorageParameters()

    def _setStorageParams(self, service_name, parameters=None, implementation=None):
        """Set storage parameters for a service.

        Centralizes the logic for converting and storing storage parameters.
        Handles Bag/dict conversion and implementation assignment.

        Args:
            service_name: Name of the storage service
            parameters: Can be a Bag, dict, or None
            implementation: Implementation type (local, symbolic, aws_s3, etc.)

        Returns:
            The stored parameters dict
        """
        # Convert parameters to dict
        if parameters:
            if isinstance(parameters, Bag):
                params = parameters.asDict()
            elif isinstance(parameters, dict):
                params = dict(parameters)
            else:
                # Try to convert to dict
                params = dict(parameters) if parameters else {}
        else:
            params = {}

        # Add implementation if provided (overrides what's in parameters)
        if implementation:
            params['implementation'] = implementation

        # Store parameters
        self.storage_params[service_name] = params
        return params

    def _loadAllStorageParameters(self):
        """Load all storage service parameters from all sources.

        Aggregates configurations from three sources with priority:
        1. Database (sys.service table) - Highest priority
        2. Site config (siteconfig.xml services section)
        3. Default configs (DEFAULT_STORAGE_CONFIGS) - Fallback

        The parameters are stored in self.storage_params as:
        {
            'service_name': {
                'implementation': 'local',
                'base_path': '/path/to/storage',
                ...other parameters...
            }
        }
        """
        # Start with default configurations
        for service_name, config in self.DEFAULT_STORAGE_CONFIGS.items():
            self.storage_params[service_name] = dict(config)

        # Add dynamic defaults that depend on site properties
        if hasattr(self.site, 'site_static_dir'):
            self._setStorageParams('home',
                parameters={'base_path': self.site.site_static_dir},
                implementation='local'
            )
            self._setStorageParams('site',
                parameters={'base_path': self.site.site_static_dir},
                implementation='local'
            )
            self._setStorageParams('mail',
                parameters={'base_path': f'{self.site.site_static_dir}/mail'},
                implementation='local'
            )

        # Override with site config
        self._loadStorageParametersFromSiteConfig()

        # Override with database config (highest priority)
        self._loadStorageParametersFromDb()

    def _loadStorageParametersFromSiteConfig(self):
        """Load storage parameters from site configuration.

        Reads from siteconfig.xml services section:
        <services>
            <storage service_name="my_storage" implementation="local">
                <base_path>/path/to/storage</base_path>
            </storage>
            <my_s3 service_type="storage" implementation="aws_s3" bucket="my-bucket" />
        </services>

        Also reads from volumes section:
        <volumes>
            <uploads path="uploads"/>
            <documents path="../documents"/>
        </volumes>
        """
        # Load from services section
        if self.site.config.get('services'):
            # Check for storage-specific section
            storage_services = self.site.config.get('services.storage')
            if storage_services:
                for service_name, service_bag in storage_services.items():
                    params = dict(service_bag.getAttr())
                    # Remove service_type if present (it's redundant)
                    params.pop('service_type', None)
                    implementation = params.pop('implementation', None)
                    self._setStorageParams(service_name, parameters=params, implementation=implementation)

            # Check for flat structure where service_type is an attribute
            all_services = self.site.config.get('services')
            if all_services:
                for service_name, service_bag in all_services.items():
                    if service_name == 'storage':  # Skip the nested section we already processed
                        continue
                    attrs = service_bag.getAttr() if hasattr(service_bag, 'getAttr') else {}
                    if attrs.get('service_type') == 'storage':
                        params = dict(attrs)
                        params.pop('service_type', None)
                        implementation = params.pop('implementation', None)
                        self._setStorageParams(service_name, parameters=params, implementation=implementation)

        # Load from volumes section (LEGACY - should be migrated to services)
        volumes = self.site.config.getItem('volumes')
        if volumes:
            logger = logging.getLogger(__name__)
            logger.warning(
                "DEPRECATED: 'volumes' configuration is legacy. "
                "Please migrate to 'services' section in siteconfig.xml. "
                "Found volumes: %s", ', '.join(volumes.keys())
            )
            for volume_name in volumes.keys():
                vpath = volumes.getAttr(volume_name, 'path')
                volume_path = expandpath(os.path.join(self.site.site_static_dir, vpath))
                self._setStorageParams(volume_name,
                    parameters={'base_path': volume_path},
                    implementation='local'
                )

    def _loadStorageParametersFromDb(self):
        """Load storage parameters from database sys.service table.

        Reads from sys.service where service_type='storage'.
        The 'parameters' column is a Bag containing additional configuration.
        """
        # Check if sys package is available
        if 'sys' not in self.site.gnrapp.packages.keys():
            return

        # Query all storage services from database
        services = self.site.db.table('sys.service').query(
            where='$service_type=:st',
            st='storage',
            order_by='$service_name',
            bagFields=True
        ).fetch()

        for service_record in services:
            service_name = service_record['service_name']
            implementation = service_record['implementation']
            parameters_bag = Bag(service_record['parameters'])

            # Use centralized method to set parameters
            self._setStorageParams(service_name,
                parameters=parameters_bag,
                implementation=implementation
            )

    def getStorageParameters(self, storage_name):
        """Get parameters for a storage service.

        Args:
            storage_name: Name of the storage service

        Returns:
            Dict with storage parameters, or None if not found
        """
        return self.storage_params.get(storage_name)

    def getAllStorageParameters(self):
        """Get all storage parameters.

        Returns:
            Dict with all storage configurations, keyed by service_name
        """
        return dict(self.storage_params)

    def debugStorageParameters(self):
        """Return a formatted string of all storage parameters for debugging.

        Returns:
            String with formatted storage configurations
        """
        lines = ["Storage Parameters:"]
        for service_name in sorted(self.storage_params.keys()):
            params = self.storage_params[service_name]
            lines.append(f"  {service_name}:")
            for key, value in sorted(params.items()):
                lines.append(f"    {key}: {value}")
        return "\n".join(lines)

    def updateStorageParams(self, service_name):
        """Update parameters for a specific storage service by reloading from database.

        This method is called by sys.service table triggers when a storage
        service configuration is modified.

        Args:
            service_name: Name of the storage service to update

        Returns:
            True if update was successful, False otherwise
        """
        # Query the specific service record
        service_record = self.site.db.table('sys.service').record(
            service_type='storage',
            service_name=service_name,
            ignoreMissing=True
        ).output('dict')

        if not service_record:
            # Service was deleted or doesn't exist, remove from params
            if service_name in self.storage_params:
                del self.storage_params[service_name]
            return True

        # Extract parameters
        implementation = service_record.get('implementation')
        parameters_bag = service_record.get('parameters')

        # Use centralized method to set parameters
        self._setStorageParams(service_name,
            parameters=parameters_bag,
            implementation=implementation
        )
        return True


    def removeStorageFromCache(self, service_name):
        """Remove a storage service from parameters.

        This method is called by sys.service table triggers when a storage
        service is deleted.

        Args:
            service_name: Name of the storage service to remove

        Returns:
            True if service was in parameters and removed, False otherwise
        """
        if service_name in self.storage_params:
            del self.storage_params[service_name]
            return True
        return False

    @deprecated('Storage services should be accessed via storage_params registry, not dynamically created')
    def getVolumeService(self, storage_name=None):
        """Get or create a volume-based local storage service.

        DEPRECATED: This method bypasses the storage_params registry and creates
        services dynamically. All storage configurations should be defined in
        database, site config, or volumes section and accessed via storage_params.

        Resolves the storage path from site configuration volumes, or uses the
        storage_name directly as a path if not configured. Creates a local storage
        service with the resolved path.

        Args:
            storage_name: Name of the storage volume, or path if not in config

        Returns:
            A storage service instance for the specified volume
        """
        sitevolumes = self.site.config.getItem('volumes')
        if sitevolumes and storage_name in sitevolumes:
            vpath = sitevolumes.getAttr(storage_name, 'path')
        else:
            vpath = storage_name
        volume_path = expandpath(os.path.join(self.site.site_static_dir, vpath))
        return self.site.getService(
            service_type='storage',
            service_name=storage_name,
            implementation='local',
            base_path=volume_path
        )

    def storagePath(self, storage_name, storage_path):
        """Adapt storage path based on storage name context.

        Prepends context-specific prefixes for special storage types:
        - 'user': Prefixes with current user
        - 'conn': Prefixes with connection ID
        - 'page': Prefixes with connection ID and page ID

        Args:
            storage_name: Type of storage (user/conn/page/other)
            storage_path: Base storage path

        Returns:
            Adapted path with appropriate context prefix
        """
        if storage_name == 'user':
            return f'{self.site.currentPage.user}/{storage_path}'
        elif storage_name == 'conn':
            return f'{self.site.currentPage.connection_id}/{storage_path}'
        elif storage_name == 'page':
            return f'{self.site.currentPage.connection_id}/{self.site.currentPage.page_id}/{storage_path}'
        return storage_path

    def storage(self, storage_name, **kwargs):
        """Get a storage service by name using stored parameters.

        Template method to be overridden by subclasses. The base implementation
        does nothing - subclasses must provide concrete implementation.

        All storage services are pre-loaded at initialization and kept
        in sync via database triggers. Implementations should use storage_params.

        Args:
            storage_name: Name of the storage service
            **kwargs: Additional arguments to override stored parameters

        Returns:
            Storage service instance, or None if service not found
        """
        # To be implemented by subclasses
        return None

    def storageNode(self, *args, **kwargs):
        """Create or return a storage node.

        Handles both string paths and existing node objects. If the first argument
        is not a string, it's treated as an existing node and either returned directly
        or used to create a new node from its fullpath.

        Args:
            *args: Path components or existing node
            **kwargs: Additional arguments passed to makeNode

        Returns:
            A storage node instance
        """
        # If first arg is already a node object, handle it
        if not isinstance(args[0], str):
            if args[1:]:
                # Node with additional path components, recurse with fullpath
                return self.storageNode(args[0].fullpath, *args[1:], **kwargs)
            else:
                # Just return the node itself
                return args[0]
        # String path, delegate to subclass implementation
        return self.makeNode(*args, **kwargs)


class LegacyStorageHandler(BaseStorageHandler):
    """Legacy storage handler implementation.

    Implements storage handling using the legacy StorageNode from gnr.lib.services.storage.
    Provides path adaptation for various legacy formats including the old 'vol:' prefix.

    Overrides the storage() method to provide concrete implementation using the
    ServiceHandler pattern to create/retrieve storage service instances.
    """

    def storage(self, storage_name, **kwargs):
        """Get a storage service by name using stored parameters.

        Concrete implementation that retrieves parameters from storage_params registry
        and uses ServiceHandler to get/create the actual storage service instance.

        All storage services are pre-loaded at initialization and kept in sync
        via database triggers. This method always uses storage_params.

        Args:
            storage_name: Name of the storage service
            **kwargs: Additional arguments to override stored parameters

        Returns:
            Storage service instance, or None if service not found
        """
        # Get stored parameters for this storage
        stored_params = self.getStorageParameters(storage_name)

        if not stored_params:
            # Service not in storage_params - should be extremely rare
            # Only happens for dynamically named services not in DB/config
            return None

        # Merge stored params with any override kwargs
        service_params = dict(stored_params)
        service_params.update(kwargs)
        # Create/get service using stored parameters
        return self.site.getService(
            service_type='storage',
            service_name=storage_name,
            **service_params
        )
    
    def _adapt_path(self, *args, **kwargs):
        """Adapt and parse legacy path formats.

        Handles multiple legacy path formats:
        - Plain paths without ':' prefix default to '_raw_:' service
        - HTTP/HTTPS URLs are prefixed with '_http_:' service
        - Legacy 'vol:name:path' format is converted to 'name/path'

        Args:
            *args: Path components to join
            **kwargs: Additional arguments (currently unused)

        Returns:
            Tuple of (service_name, storage_path)
        """
        path = '/'.join(args)

        # Add default service prefix if none specified
        if ':' not in path:
            path = f'_raw_:{path}'

        # Handle HTTP/HTTPS URLs
        if path.startswith('http://') or path.startswith('https://'):
            path = f'_http_:{path}'

        # Split into service name and path
        service_name, storage_path = path.split(':', 1)
        storage_path = storage_path.lstrip('/')

        # Handle legacy 'vol:' prefix format
        if service_name == 'vol':
            # Old format: vol:volumename:path -> volumename/path
            service_name, storage_path = storage_path.replace(':', '/').split('/', 1)

        return service_name, storage_path

    def makeNode(self, *args, **kwargs):
        """Create a legacy storage node.

        Adapts the path, resolves the storage service, applies context-based path
        adaptation if requested, and creates a LegacyStorageNode instance.

        Args:
            *args: Path components
            **kwargs: Additional arguments passed to StorageNode, plus:
                _adapt: If True (default), apply context-based path adaptation
                autocreate: Auto-create directories if needed
                must_exist: Raise exception if path doesn't exist
                mode: File mode ('r', 'w', etc.)
                version: Version identifier for versioned storage

        Returns:
            LegacyStorageNode instance, or None if service unavailable
        """
        service_name, storage_path = self._adapt_path(*args, **kwargs)
        service = self.storage(service_name)

        # Apply context-based path adaptation if requested
        if kwargs.pop('_adapt', True):
            storage_path = self.storagePath(service_name, storage_path)

        if not service:
            return None

        # Extract StorageNode-specific parameters
        autocreate = kwargs.pop('autocreate', False)
        must_exist = kwargs.pop('must_exist', False)
        mode = kwargs.pop('mode', None)
        version = kwargs.pop('version', None)

        return LegacyStorageNode(
            parent=self.site,
            service=service,
            path=storage_path,
            autocreate=autocreate,
            must_exist=must_exist,
            mode=mode,
            version=version
        )


class NewStorageNode:
    """Wrapper class for BrickStorageNode to provide LegacyStorageNode-compatible interface.

    This class wraps a BrickStorageNode instance and adapts its API to match the
    LegacyStorageNode interface used throughout Genropy. It uses __getattr__ to delegate
    compatible method calls directly to the wrapped BrickStorageNode, while providing
    adapter methods for API differences.

    API Compatibility:
        Direct delegation (identical APIs):
            - fullpath, path, exists, isfile, isdir, size, mtime, basename
            - md5hash, versions, ext_attributes, mimetype
            - open(), delete(), mkdir(), children()
            - url(), internal_url(), serve(), local_path()
            - get_metadata(), set_metadata()

        Adapted methods (different APIs):
            - cleanbasename → stem
            - dirname → adapted to return fullpath format
            - parentStorageNode → parent
            - move() → move_to()
            - copy() → copy_to()
            - base64() → to_base64()
            - ext → suffix (with dot removal)
            - child() → child() with different path handling

    Args:
        brick_node: The BrickStorageNode instance to wrap
        parent: The site instance (for compatibility with legacy code)
        service_name: The storage service name for fullpath construction
    """

    def __init__(self, brick_node, parent=None, service_name=None):
        """Initialize the wrapper.

        Args:
            brick_node: BrickStorageNode instance from genro-storage
            parent: Site instance for legacy compatibility
            service_name: Storage service name
        """
        self._brick_node = brick_node
        self.parent = parent
        self.service_name = service_name
        # Legacy compatibility attributes
        self.service = None  # For legacy code that checks node.service
        self.mode = 'r'
        self.autocreate = False
        self.version = None

    def __str__(self):
        """String representation matching LegacyStorageNode format."""
        return f'NewStorageNode <{self._brick_node.fullpath}>'

    def __getattr__(self, name):
        """Delegate attribute access to wrapped BrickStorageNode for compatible APIs.

        This method is called when an attribute is not found in NewStorageNode.
        It delegates to BrickStorageNode for all compatible methods/properties.

        Note: url() and internal_url() are implemented as methods below, not delegated.
        """
        # Direct delegation for compatible APIs (excluding url/internal_url which we override)
        compatible_attrs = {
            'fullpath', 'path', 'exists', 'isfile', 'isdir', 'size', 'mtime',
            'basename', 'md5hash', 'versions', 'ext_attributes', 'mimetype',
            'open', 'delete', 'mkdir', 'children',
            'serve', 'local_path', 'get_metadata', 'set_metadata', 'splitext',
            'fill_from_url'
        }

        if name in compatible_attrs:
            return getattr(self._brick_node, name)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # Adapted properties and methods

    @property
    def cleanbasename(self):
        """Returns basename without extension (legacy name for 'stem')."""
        return self._brick_node.stem

    @property
    def ext(self):
        """Returns file extension without leading dot."""
        suffix = self._brick_node.suffix
        return suffix.lstrip('.') if suffix else ''

    @property
    def dirname(self):
        """Returns the fullpath of parent directory in legacy format."""
        # BrickStorageNode.dirname returns just the path, we need fullpath format
        return self._brick_node.parent.fullpath if self._brick_node.parent else ''

    @property
    def parentStorageNode(self):
        """Returns the StorageNode pointing to the parent directory."""
        parent_brick = self._brick_node.parent
        if parent_brick and self.parent:
            return NewStorageNode(parent_brick, parent=self.parent, service_name=self.service_name)
        return None

    @property
    def internal_path(self):
        """Returns the internal filesystem path (absolute path for local storage).

        For local storages, this returns the resolved absolute filesystem path.
        For remote storages (S3, etc.), this returns the relative path within the storage.

        Uses genro-storage's public resolved_path API (genro-storage >= 0.5.1).
        See: https://github.com/genropy/genro-storage/issues/59
        """
        # Use public API for resolved path (genro-storage >= 0.5.1)
        resolved = self._brick_node.resolved_path
        if resolved is not None:
            return resolved

        # Fallback to relative path for remote storages
        return self._brick_node.path

    def base64(self, mime=None):
        """Returns base64 encoded string of file content (legacy API)."""
        include_uri = mime is not None
        return self._brick_node.to_base64(mime=mime, include_uri=include_uri)

    def move(self, dest=None):
        """Moves the file to another path (legacy API).

        Args:
            dest: Destination path or StorageNode
        """
        # Convert dest to appropriate format
        if isinstance(dest, NewStorageNode):
            dest_node = dest._brick_node
        elif isinstance(dest, str):
            # If string, create a node for it
            # This requires access to storage manager - simplified for now
            dest_node = dest
        else:
            dest_node = dest

        result = self._brick_node.move_to(dest_node)

        # Update self to point to new location (legacy behavior)
        self._brick_node = result
        return result

    def copy(self, dest=None):
        """Copies the file to another path (legacy API).

        Args:
            dest: Destination path or StorageNode

        Returns:
            NewStorageNode pointing to the copy
        """
        if isinstance(dest, NewStorageNode):
            dest_node = dest._brick_node
        elif isinstance(dest, str):
            dest_node = dest
        else:
            dest_node = dest

        result = self._brick_node.copy_to(dest_node)
        return NewStorageNode(result, parent=self.parent, service_name=self.service_name)

    def child(self, path=None):
        """Returns a StorageNode pointing to a sub path (legacy API).

        Args:
            path: Relative path to child

        Returns:
            NewStorageNode for the child path
        """
        # Legacy behavior: adds '/' if not present
        if self._brick_node.path and not self._brick_node.path.endswith('/'):
            path = f'/{path}'

        child_brick = self._brick_node.child(path)
        return NewStorageNode(child_brick, parent=self.parent, service_name=self.service_name)

    def listdir(self):
        """Returns list of file/dir names contained (if isdir) - legacy API."""
        if self.isdir:
            return [child.basename for child in self._brick_node.children()]
        return []

    def url(self, **kwargs):
        """Generate external URL for this storage node.

        TEMPORARY WORKAROUND: genro-storage's BrickStorageNode.url() returns None for local mounts.
        See GENRO_STORAGE_ISSUE.md for details. This method will be removed once genro-storage
        properly supports URL generation for local storages.

        We override to generate URLs in Genropy's expected format: {external_host}/_storage/{service}/{path}

        Args:
            **kwargs: URL parameters (passed to internal_url)

        Returns:
            URL string
        """
        return self.internal_url(**kwargs)

    def internal_url(self, **kwargs):
        """Generate internal URL for this storage node.

        TEMPORARY WORKAROUND: See url() method comment. This will be removed once genro-storage
        has native URL generation support.

        Generates service-specific URLs to match legacy Genropy URL patterns:
        - rsrc: {external_host}/_rsrc/{resource_id}/{path}
        - pkg: {external_host}/_pkg/{package_name}/{path}
        - pages: {external_host}/_pages/{path}
        - gnr: {external_host}/_gnr/{version}/{path}
        - dojo: {external_host}/_dojo/{version}/{path}
        - other: {external_host}/_storage/{service_name}/{path}

        Args:
            **kwargs: URL parameters
                nocache: If True, adds mtime-based cache-busting parameter
                Other kwargs are added as query parameters

        Returns:
            URL string
        """
        if not self.parent or not hasattr(self.parent, 'external_host'):
            # Fallback if no parent site available
            return self._generate_url_pattern(self.service_name, self._brick_node.path, '')

        external_host = self.parent.external_host.rstrip('/')
        url = self._generate_url_pattern(self.service_name, self._brick_node.path, external_host)

        if not kwargs:
            return url

        nocache = kwargs.pop('nocache', None)
        if nocache:
            # Check exists before accessing mtime (genro-storage design pattern)
            # mtime raises FileNotFoundError for non-existent files
            # See: https://github.com/genropy/genro-storage/issues/58
            if self._brick_node.exists:
                mtime = self._brick_node.mtime
            else:
                mtime = random.random() * 100000
            kwargs['mtime'] = '%0.0f' % (mtime)

        if kwargs:
            url = f'{url}?{urlencode(kwargs)}'

        return url

    def _generate_url_pattern(self, service_name, path, external_host):
        """Generate service-specific URL pattern.

        Different storage services use different URL patterns in Genropy:
        - rsrc, pkg: first path component is resource_id/package_name
        - pages: direct path mapping
        - gnr, dojo: first path component is version (but these are handled by StaticHandler)
        - others: generic /_storage/ pattern

        Args:
            service_name: Name of storage service (rsrc, pkg, pages, etc.)
            path: Relative path in storage
            external_host: External host URL (may be empty string)

        Returns:
            Complete URL string
        """
        # Parse path components
        parts = path.split('/', 1) if path else ['']
        first_component = parts[0]
        rest_path = parts[1] if len(parts) > 1 else ''

        # Generate service-specific URL pattern
        if service_name == 'rsrc':
            # Format: /_rsrc/{resource_id}/{remaining_path}
            url = f'{external_host}/_rsrc/{first_component}'
            if rest_path:
                url = f'{url}/{rest_path}'
        elif service_name == 'pkg':
            # Format: /_pkg/{package_name}/{remaining_path}
            url = f'{external_host}/_pkg/{first_component}'
            if rest_path:
                url = f'{url}/{rest_path}'
        elif service_name == 'pages':
            # Format: /_pages/{path}
            url = f'{external_host}/_pages/{path}'
        elif service_name in ('gnr', 'dojo'):
            # Format: /_gnr/{version}/{path} or /_dojo/{version}/{path}
            # Note: These should be handled by LegacyGnrStaticAdapter, but include pattern for completeness
            url = f'{external_host}/_{service_name}/{first_component}'
            if rest_path:
                url = f'{url}/{rest_path}'
        else:
            # Generic pattern for other storages
            url = f'{external_host}/_storage/{service_name}/{path}'

        return url

    def kwargs_url(self, **kwargs):
        """Get URL with kwargs support (nocache, etc).

        Similar to url() but handles special kwargs like 'nocache' that add
        query parameters based on file modification time.

        This method is kept for compatibility but now delegates to internal_url().

        Args:
            **kwargs: URL parameters
                nocache: If True, adds mtime-based cache-busting parameter
                Other kwargs are added as query parameters

        Returns:
            URL string with query parameters
        """
        # Use internal_url() which already handles nocache and other kwargs
        return self.internal_url(**kwargs)

    def serve(self, environ, start_response, **kwargs):
        """Serve the file content via WSGI.

        This method handles HTTP file serving with support for:
        - ETags for caching
        - Download/attachment mode
        - Cache control headers

        Args:
            environ: WSGI environment dict
            start_response: WSGI start_response callable
            **kwargs: Additional options:
                download: If True, serve as download
                download_name: Custom filename for download
                file: Ignored (legacy compatibility)

        Returns:
            WSGI response iterable
        """
        from paste import fileapp
        from paste.httpheaders import ETAG

        # Remove 'file' kwarg if present (legacy compatibility)
        kwargs.pop('file', None)

        # Check if file exists
        if not self.exists:
            # Return 404
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'File not found']

        # Get internal path for FileApp
        fullpath = self.internal_path
        if not fullpath:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'File not found']

        # Handle ETag for caching
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            if_none_match = if_none_match.replace('"', '')
            try:
                mytime = self.mtime
                size = self.size
                my_none_match = f"{mytime}-{size}"
                if my_none_match == if_none_match:
                    headers = []
                    ETAG.update(headers, my_none_match)
                    start_response('304 Not Modified', headers)
                    return [b'']  # empty body
            except:
                pass  # If mtime/size fail, continue without ETag

        # Handle download mode
        file_args = {}
        download = kwargs.get('download', False)
        download_name = kwargs.get('download_name')
        if download or download_name:
            import os
            download_name = download_name or os.path.basename(fullpath)
            file_args['content_disposition'] = f"attachment; filename={download_name}"

        # Use FileApp to serve the file
        file_responder = fileapp.FileApp(fullpath, **file_args)

        # Add cache control if configured
        if hasattr(self.parent, 'cache_max_age') and self.parent.cache_max_age:
            file_responder.cache_control(max_age=self.parent.cache_max_age)

        return file_responder(environ, start_response)


class LegacyStorageServiceAdapter:
    """Minimal adapter service that delegates to storageNode().

    This class provides backward compatibility for legacy code that uses
    site.storage('name').method() pattern by internally delegating to
    site.storageNode() calls.

    Args:
        handler: The NewStorageHandler instance
        service_name: Name of the storage service/mount
    """

    def __init__(self, handler, service_name):
        """Initialize the minimal service adapter.

        Args:
            handler: NewStorageHandler instance for storageNode() delegation
            service_name: Name of the storage mount
        """
        self.handler = handler
        self.service_name = service_name

    def url(self, *args, **kwargs):
        """Get URL for the given path.

        Args:
            *args: Path components
            **kwargs: Additional parameters passed to node.url()

        Returns:
            URL string or None
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.url(**kwargs) if node else None

    def kwargs_url(self, *args, **kwargs):
        """Get URL with kwargs support (nocache, etc).

        Args:
            *args: Path components
            **kwargs: URL parameters (nocache, etc)

        Returns:
            URL string with query parameters
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.kwargs_url(**kwargs) if node else None

    def path(self, *args):
        """Get local filesystem path.

        Args:
            *args: Path components

        Returns:
            Local path string or None
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        if not node:
            return None

        # Try to get internal_url which might be a local path
        internal = node.internal_url()
        if internal and not internal.startswith('http'):
            return internal

        return None

    def open(self, *args, **kwargs):
        """Open file at the given path.

        Args:
            *args: Path components
            **kwargs: Open mode and other parameters

        Returns:
            File-like object
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        mode = kwargs.get('mode', 'rb')
        return node.open(mode=mode)

    def exists(self, *args):
        """Check if file/directory exists at the given path.

        Args:
            *args: Path components

        Returns:
            bool: True if exists, False otherwise
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.exists if node else False

    def mtime(self, *args):
        """Get modification time of file at the given path.

        Args:
            *args: Path components

        Returns:
            float: Modification time timestamp, or 0 if file doesn't exist
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        # Check exists before accessing mtime (genro-storage design pattern)
        # mtime raises FileNotFoundError for non-existent files
        # See: https://github.com/genropy/genro-storage/issues/58
        if not node or not node.exists:
            return 0
        return node.mtime

    def size(self, *args):
        """Get size of file at the given path.

        Args:
            *args: Path components

        Returns:
            int: File size in bytes
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.size if node else None

    def isdir(self, *args):
        """Check if path is a directory.

        Args:
            *args: Path components

        Returns:
            bool: True if directory, False otherwise
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.isdir if node else False

    def isfile(self, *args):
        """Check if path is a file.

        Args:
            *args: Path components

        Returns:
            bool: True if file, False otherwise
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        return node.isfile if node else False

    def internal_path(self, *args):
        """Get internal filesystem path for the given path.

        Args:
            *args: Path components

        Returns:
            str: Internal filesystem path or None
        """
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        if not node:
            return None

        # For NewStorageNode, use internal_path property
        if hasattr(node, 'internal_path') and not callable(node.internal_path):
            return node.internal_path

        # For BrickStorageNode, try to get the resolved filesystem path
        if hasattr(node, '_brick_node'):
            brick = node._brick_node
            # For local storage backends, access the resolved path
            if hasattr(brick, '_backend') and hasattr(brick._backend, '_resolve_path'):
                try:
                    return brick._backend._resolve_path(brick._path)
                except:
                    pass

        return None


class LegacyGnrStaticAdapter:
    """Adapter for GnrStaticHandler to provide storage service API.

    This adapter wraps GnrStaticHandler to provide the expected storage service
    interface with internal_path() method that legacy code expects.

    GnrStaticHandler has path() method but not internal_path().
    This adapter bridges that gap.

    Args:
        static_handler: The GnrStaticHandler or DojoStaticHandler instance
    """

    def __init__(self, static_handler):
        """Initialize the adapter.

        Args:
            static_handler: GnrStaticHandler or DojoStaticHandler instance
        """
        self.static_handler = static_handler

    def url(self, *args, **kwargs):
        """Get URL for the given path.

        Args:
            *args: Path components (first arg is typically version)
            **kwargs: Additional parameters

        Returns:
            URL string
        """
        return self.static_handler.url(*args, **kwargs)

    def kwargs_url(self, *args, **kwargs):
        """Get URL with kwargs support.

        Args:
            *args: Path components (first arg is typically version)
            **kwargs: URL parameters

        Returns:
            URL string with query parameters
        """
        return self.static_handler.kwargs_url(*args, **kwargs)

    def path(self, *args, **kwargs):
        """Get local filesystem path.

        Args:
            *args: Path components (first arg is typically version)
            **kwargs: Additional parameters

        Returns:
            Local filesystem path string
        """
        return self.static_handler.path(*args, **kwargs)

    def internal_path(self, *args, **kwargs):
        """Get internal filesystem path.

        This is an alias for path() to provide compatibility with
        storage service API that expects internal_path() method.

        Args:
            *args: Path components (first arg is typically version)
            **kwargs: Additional parameters

        Returns:
            Local filesystem path string
        """
        return self.static_handler.path(*args, **kwargs)

    def mtime(self, *args, **kwargs):
        """Get modification time of file.

        Args:
            *args: Path components (first arg is typically version)
            **kwargs: Additional parameters

        Returns:
            float: Modification time timestamp, or 0 if file doesn't exist
        """
        import os
        # Get the filesystem path
        file_path = self.static_handler.path(*args, **kwargs)

        if not file_path:
            return 0

        # Get mtime from filesystem
        try:
            return os.path.getmtime(file_path)
        except (OSError, TypeError):
            return 0


class NewStorageHandler(BaseStorageHandler):
    """Storage handler using genro-storage library (BrickStorageNode).

    This handler inherits from BaseStorageHandler and uses the genro-storage library
    to provide a modern, unified storage abstraction. It converts storage_params
    configurations into StorageManager mount configurations and wraps BrickStorageNode
    instances in NewStorageNode for API compatibility.

    Configuration mapping:
        - 'local' implementation → 'local' type
        - 'aws_s3' implementation → 's3' type
        - 'symbolic' implementation → 'local' type with dynamic paths
        - 'http'/'raw' implementation → 'http' type

    Args:
        site: The GnrWsgiSite instance
    """

    def __init__(self, site):
        """Initialize the storage handler with StorageManager.

        Args:
            site: The GnrWsgiSite instance
        """
        super().__init__(site)

        # Create StorageManager instance
        self.storage_manager = StorageManager()

        # Configure storage manager from storage_params
        self._configureStorageManager()

    def _configureStorageManager(self):
        """Configure StorageManager from storage_params registry.

        Converts storage_params dict into StorageManager mount configurations.
        Maps Genropy storage implementations to genro-storage backend types.

        Note: 'gnr' and 'dojo' storages are excluded from genro-storage because they use
        version-specific path resolution that is incompatible with genro-storage's static
        base_path model. See GENRO_STORAGE_ISSUE.md Issue #2 for details.
        """
        import logging
        logger = logging.getLogger(__name__)

        mount_configs = []
        logger.debug(f"Configuring StorageManager with {len(self.storage_params)} storage services")

        for service_name, params in self.storage_params.items():
            # Skip gnr, dojo - they use version-specific path resolution incompatible with genro-storage
            # These are handled by StaticHandler instead
            # Note: rsrc and pkg now use switched mount pattern (callable with parameter)
            if service_name in ('gnr', 'dojo'):
                logger.debug(f"Skipping {service_name} (handled by StaticHandler)")
                continue

            mount_config = self._adaptStorageParamsToMount(service_name, params)
            if mount_config:
                logger.debug(f"Creating mount for '{service_name}': type={mount_config.get('type')}")
                mount_configs.append(mount_config)
            else:
                logger.warning(f"Failed to create mount config for '{service_name}' with params: {params}")

        # Configure all mounts at once
        if mount_configs:
            logger.debug(f"Configuring {len(mount_configs)} mounts in StorageManager")
            try:
                self.storage_manager.configure(mount_configs)
                logger.debug(f"Available mounts: {list(self.storage_manager._mounts.keys())}")
            except Exception as e:
                logger.error(f"Failed to configure StorageManager: {e}", exc_info=True)
                logger.error(f"Mount configs that failed: {mount_configs}")
                raise
        else:
            logger.warning("No mount configs created!")

    def _makeSymbolicPathCallable(self, service_name):
        """Create a callable that resolves symbolic storage path dynamically.

        Symbolic storages like 'dojo', 'gnr', 'rsrc', 'pkg' resolve their paths
        based on site configuration and package locations at runtime.

        Args:
            service_name: Name of the symbolic storage service

        Returns:
            Callable that returns the resolved absolute path when invoked
        """
        def resolve_symbolic_path():
            """Resolve the symbolic storage path at runtime."""
            # For 'gnr' and 'dojo', use site.gnr_path or site.dojo_path to get versioned directory
            # These have version-specific paths (e.g., gnr_d11, dojo1.11)
            if service_name == 'gnr':
                # gnr_path is a dict like {'11': '/path/to/gnrjs/gnr_d11', ...}
                # Use the first/default version's path
                if hasattr(self.site, 'gnr_path') and self.site.gnr_path:
                    # Get first version's base path
                    first_version_path = next(iter(self.site.gnr_path.values()))
                    return first_version_path
                # Fallback
                return os.path.join(self.site.site_static_dir, 'gnr')
            elif service_name == 'dojo':
                # Similar logic for dojo
                if hasattr(self.site, 'dojo_path') and self.site.dojo_path:
                    first_version_path = next(iter(self.site.dojo_path.values()))
                    return first_version_path
                # Fallback
                return os.path.join(self.site.site_static_dir, 'dojo')
            elif service_name == 'rsrc':
                # Common resources
                if hasattr(self.site, 'resources_path'):
                    return self.site.resources_path
                return os.path.join(self.site.site_path, 'resources')
            elif service_name == 'pkg':
                # Package resources - use site_static_dir as base
                # Actual package resolution happens in storagePath()
                return self.site.site_static_dir
            elif service_name == 'pages':
                # Pages directory
                return os.path.join(self.site.site_path, 'pages')
            elif service_name in ('user', 'conn', 'page'):
                # Context-dependent storages - these need the base data directory
                # Actual user/conn/page resolution happens in storagePath()
                if service_name == 'user':
                    return os.path.join(self.site.site_path, 'data', 'users')
                elif service_name == 'conn':
                    return os.path.join(self.site.site_path, 'data', 'connections')
                elif service_name == 'page':
                    return os.path.join(self.site.site_path, 'data', 'pages')
            elif service_name == 'temp':
                # Temporary storage
                return os.path.join(self.site.site_path, 'data', 'temp')
            else:
                # Fallback to site_static_dir for unknown symbolic storages
                return self.site.site_static_dir

        return resolve_symbolic_path

    def _makeRsrcPathResolver(self):
        """Create a callable that resolves rsrc paths using site.resources dict.

        Uses genro-storage's "switched mount" pattern where the callable accepts
        a parameter (resource_id) and returns the corresponding base path.

        The first path component (resource_id) is extracted and looked up in
        site.resources dict to get the actual filesystem path.

        Example:
            rsrc:common/images/logo.png
            -> resource_id='common' -> site.resources['common'] -> /path/to/common
            -> final path: /path/to/common/images/logo.png

        Returns:
            Callable that accepts resource_id and returns base path

        See: https://github.com/genropy/genro-storage/issues/60
        """
        def resolve_rsrc_path(resource_id):
            """Resolve resource_id to actual filesystem path."""
            if not hasattr(self.site, 'resources') or not self.site.resources:
                raise ValueError(f"site.resources not configured")

            base_path = self.site.resources.get(resource_id)
            if not base_path:
                raise ValueError(f"Unknown resource_id: {resource_id}")

            return expandpath(base_path)

        return resolve_rsrc_path

    def _makePkgPathResolver(self):
        """Create a callable that resolves pkg paths using site.packages dict.

        Uses genro-storage's "switched mount" pattern where the callable accepts
        a parameter (package_name) and returns the corresponding base path.

        The first path component (package_name) is extracted and looked up in
        site.packages dict to get the actual package filesystem path.

        Example:
            pkg:gnrcore/pwa/conf.xml
            -> package_name='gnrcore' -> site.packages['gnrcore'] -> /path/to/gnrcore
            -> final path: /path/to/gnrcore/pwa/conf.xml

        Returns:
            Callable that accepts package_name and returns base path

        See: https://github.com/genropy/genro-storage/issues/60
        """
        def resolve_pkg_path(package_name):
            """Resolve package_name to actual filesystem path."""
            if not hasattr(self.site, 'packages') or not self.site.packages:
                raise ValueError(f"site.packages not configured")

            package_obj = self.site.packages.get(package_name)
            if not package_obj:
                raise ValueError(f"Unknown package: {package_name}")

            # Package object has packageFolder attribute
            if hasattr(package_obj, 'packageFolder'):
                return expandpath(package_obj.packageFolder)
            else:
                raise ValueError(f"Package {package_name} has no packageFolder attribute")

        return resolve_pkg_path

    def _adaptStorageParamsToMount(self, service_name, params):
        """Adapt storage_params to StorageManager mount configuration.

        Args:
            service_name: Name of the storage service
            params: Storage parameters dict

        Returns:
            Mount configuration dict for StorageManager, or None if not applicable
        """
        if not params:
            return None

        implementation = params.get('implementation')

        # Map Genropy implementations to genro-storage types
        type_mapping = {
            'local': 'local',
            'symbolic': 'local',  # Symbolic also uses local type
            'aws_s3': 's3',
            's3': 's3',
            'http': 'http',
            'raw': 'local',  # Raw files use local type
            'memory': 'memory',
        }

        storage_type = type_mapping.get(implementation)

        if not storage_type:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Unknown storage implementation '{implementation}' for service '{service_name}'. "
                "Skipping mount configuration."
            )
            return None

        # Build mount configuration
        mount_config = {
            'name': service_name,
            'type': storage_type
        }

        # Add type-specific parameters
        if storage_type == 'local':
            # For local storage, we need a base_path
            base_path = params.get('base_path')
            if base_path:
                mount_config['path'] = expandpath(base_path)
            elif service_name == 'rsrc':
                # rsrc uses switched mount pattern: callable with parameter (resource_id)
                # See: https://github.com/genropy/genro-storage/issues/60
                mount_config['path'] = self._makeRsrcPathResolver()
            elif service_name == 'pkg':
                # pkg uses switched mount pattern: callable with parameter (package_name)
                # See: https://github.com/genropy/genro-storage/issues/60
                mount_config['path'] = self._makePkgPathResolver()
            elif implementation == 'symbolic':
                # Symbolic storage uses dynamic path resolution via callable
                # Create a callable that resolves the path based on service_name
                mount_config['path'] = self._makeSymbolicPathCallable(service_name)
            elif implementation == 'raw':
                # Raw storage uses absolute filesystem paths
                mount_config['path'] = '/'

            # Add base_url for URL generation (genro-storage >= 0.5.1)
            # See: https://github.com/genropy/genro-storage/issues/55
            if 'base_url' in params:
                mount_config['base_url'] = params['base_url']

        elif storage_type == 's3':
            # S3-specific parameters
            # Map Genropy parameter names to genro-storage parameter names
            if 'bucket' in params:
                mount_config['bucket'] = params['bucket']
            # Region can be 'region' or 'region_name'
            if 'region_name' in params:
                mount_config['region'] = params['region_name']
            elif 'region' in params:
                mount_config['region'] = params['region']
            # Credentials can use AWS standard names or short names
            if 'aws_access_key_id' in params:
                mount_config['key'] = params['aws_access_key_id']
            elif 'access_key' in params:
                mount_config['key'] = params['access_key']
            if 'aws_secret_access_key' in params:
                mount_config['secret'] = params['aws_secret_access_key']
            elif 'secret_key' in params:
                mount_config['secret'] = params['secret_key']
            # S3 prefix/base_path
            if 'base_path' in params and params['base_path']:
                mount_config['prefix'] = params['base_path']

        elif storage_type == 'http':
            # HTTP storage - placeholder for HTTP URLs
            # Actual URL is provided at node creation time
            mount_config['base_url'] = params.get('base_url', '')

        # Add permission level if specified
        if 'permission' in params:
            mount_config['permission'] = params['permission']

        # Copy other parameters that might be relevant
        for key in ['endpoint_url', 'prefix', 'readonly']:
            if key in params:
                mount_config[key] = params[key]

        return mount_config

    def storage(self, storage_name, **kwargs):
        """Get storage service adapter.

        Returns a LegacyStorageServiceAdapter instance that provides legacy
        StorageService-compatible API (url, path, open, kwargs_url methods).

        Note: For 'gnr' and 'dojo' storages, this delegates directly to GnrStaticHandler
        because these use version-specific path resolution incompatible with genro-storage.
        See GENRO_STORAGE_ISSUE.md Issue #2 for details.

        DEPRECATED: The returned adapter's methods are all deprecated. Use
        site.storageNode('service:path').method() directly in new code.

        Args:
            storage_name: Name of the storage service
            **kwargs: Additional parameters (currently unused, for compatibility)

        Returns:
            LegacyStorageServiceAdapter instance, or None if mount not found
        """
        # For gnr, dojo: delegate to their respective StaticHandlers
        # These have version-specific path resolution incompatible with genro-storage
        # Wrap with adapter to provide internal_path() method that legacy code expects
        # Note: rsrc and pkg now use switched mount pattern in genro-storage
        if storage_name in ('gnr', 'dojo'):
            static_handler = self.site.getStatic(storage_name)
            return LegacyGnrStaticAdapter(static_handler)

        if self.storage_manager.has_mount(storage_name):
            return LegacyStorageServiceAdapter(
                handler=self,
                service_name=storage_name
            )
        return None

    def makeNode(self, *args, **kwargs):
        """Create a NewStorageNode instance wrapping BrickStorageNode.

        Template method implementation that creates storage nodes using genro-storage.
        Unlike LegacyStorageHandler, this works directly with fullpath format since
        StorageManager handles path parsing internally.

        Args:
            *args: Path components (supports both 'service:path' and separate args)
            **kwargs: Additional arguments:
                _adapt: If True (default), apply context-based path adaptation
                autocreate: Auto-create directories if needed
                must_exist: Raise exception if path doesn't exist
                mode: File mode ('r', 'w', etc.)
                version: Version identifier for versioned storage

        Returns:
            NewStorageNode instance wrapping BrickStorageNode, or None if mount not found
        """
        # Build fullpath from args
        path = '/'.join(args)

        # Add default service prefix if none specified
        if ':' not in path:
            path = f'_raw_:{path}'

        # Handle HTTP/HTTPS URLs
        if path.startswith('http://') or path.startswith('https://'):
            path = f'_http_:{path}'

        # Extract service name for context-based adaptation
        service_name = path.split(':', 1)[0]
        storage_path = path.split(':', 1)[1].lstrip('/')

        # Apply context-based path adaptation if requested
        if kwargs.pop('_adapt', True):
            storage_path = self.storagePath(service_name, storage_path)
            # Rebuild fullpath with adapted path
            path = f'{service_name}:{storage_path}'

        # Check if mount exists
        if not self.storage_manager.has_mount(service_name):
            # For gnr, dojo: delegate to legacy handler (version-specific paths)
            # Note: rsrc and pkg now use switched mount pattern in genro-storage
            if service_name in ('gnr', 'dojo'):
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Delegating {service_name} node creation to legacy handler")
                # Use legacy handler for these special storages
                legacy_handler = LegacyStorageHandler(self.site)
                return legacy_handler.makeNode(*args, **kwargs)

            import logging
            logger = logging.getLogger(__name__)
            available_mounts = list(self.storage_manager._mounts.keys()) if hasattr(self.storage_manager, '_mounts') else 'unknown'
            logger.error(
                f"Storage mount '{service_name}' not found for path '{path}'. "
                f"Available mounts: {available_mounts}. "
                f"Original args: {args}"
            )
            return None

        # Extract parameters
        autocreate = kwargs.pop('autocreate', False)
        must_exist = kwargs.pop('must_exist', False)
        mode = kwargs.pop('mode', None)
        version = kwargs.pop('version', None)

        # Convert Genropy's '_latest_' convention to None for genro-storage
        # Legacy code uses '_latest_' as a special marker for the current version,
        # but genro-storage expects None to mean "get the latest/current version"
        if version == '_latest_':
            version = None

        # Create BrickStorageNode using StorageManager
        # StorageManager.node() handles the fullpath parsing internally
        brick_node = self.storage_manager.node(path, version=version)

        # Handle autocreate
        if autocreate and not brick_node.exists:
            if autocreate == -1:  # Create parent directory
                brick_node.parent.mkdir(parents=True, exist_ok=True)
            else:
                brick_node.mkdir(parents=True, exist_ok=True)

        # Handle must_exist
        if must_exist and not brick_node.exists:
            from gnr.lib.services.storage import NotExistingStorageNode
            raise NotExistingStorageNode(f"Storage node {path} does not exist")

        # Wrap in NewStorageNode
        wrapped_node = NewStorageNode(
            brick_node=brick_node,
            parent=self.site,
            service_name=service_name
        )

        # Set mode if provided
        if mode:
            wrapped_node.mode = mode
        if version:
            wrapped_node.version = version
        if autocreate:
            wrapped_node.autocreate = autocreate

        return wrapped_node


def StorageHandler(site):
    """Factory function to create appropriate storage handler based on site configuration.

    Reads site.config['storage?mode'] to determine which handler to instantiate:
    - 'ns': Returns NewStorageHandler (uses genro-storage library)
    - 'legacy' or None: Returns LegacyStorageHandler (default)

    Args:
        site: GnrWsgiSite instance

    Returns:
        BaseStorageHandler subclass instance (either NewStorageHandler or LegacyStorageHandler)

    Example siteconfig.xml:
        <storage mode="ns"/>        <!-- Use genro-storage -->
        <storage mode="legacy"/>    <!-- Use legacy (default) -->
        <storage/>                  <!-- Use legacy (default) -->
    """
    logger = logging.getLogger(__name__)
    storage_mode = site.config['storage?mode'] or 'legacy'

    if storage_mode == 'ns':
        logger.debug("Initializing NewStorageHandler (genro-storage)")
        return NewStorageHandler(site)
    else:
        logger.debug("Initializing LegacyStorageHandler")
        return LegacyStorageHandler(site)


