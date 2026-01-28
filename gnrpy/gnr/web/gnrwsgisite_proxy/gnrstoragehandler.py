#!/usr/bin/env python
# encoding: utf-8
"""
Storage Handler Module

This module provides storage handling functionality for Genropy web applications.
It implements a proxy pattern to manage storage nodes and services, supporting both
legacy storage implementations and preparing for future brick storage integration.

The module defines:
- BaseStorageHandler: Base class with core storage operations
- LegacyStorageHandler: Implementation using legacy StorageNode
- BaseStorageNode: Base class for future storage node implementations
"""

import os

from gnr.lib.services.storage import StorageNode as LegacyStorageNode
from gnr.core.gnrsys import expandpath
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import deprecated
from gnr.web import logger

# Future integration with genro_storage brick implementation
# from genro_storage import StorageNode as BrickStorageNode


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

    def __init__(self, site, domain=None):
        """Initialize the storage handler.

        Args:
            site: The GnrWsgiSite instance
            domain: The domain this handler belongs to (for multidomain mode).
                    If None, uses site.currentDomain at query time.
        """
        self.site = site
        self.domain = domain
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
        # Load from services section (mimics ServiceHandler.serviceConfigurationsFromSiteConfig)
        services = self.site.config['services']
        if services:
            # Check for storage-specific section: <services><storage>...</storage></services>
            storage_services = self.site.config['services.storage']
            if storage_services:
                for service_name, attrs in storage_services.digest('#k,#a'):
                    attrs = dict(attrs) if attrs else {}
                    attrs.pop('service_type', None)
                    implementation = attrs.pop('implementation', None)
                    self._setStorageParams(service_name, parameters=attrs, implementation=implementation)
            # Also check flat structure: <services><my_storage service_type="storage" .../></services>
            for service_name, attrs in services.digest('#k,#a'):
                attrs = dict(attrs) if attrs else {}
                service_type = attrs.pop('service_type', None) or service_name
                if service_type == 'storage':
                    implementation = attrs.pop('implementation', None)
                    self._setStorageParams(service_name, parameters=attrs, implementation=implementation)

        # Load from volumes section (LEGACY - should be migrated to services)
        volumes = self.site.config.getItem('volumes')
        if volumes:
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
        # Use explicit domain if set, otherwise fall back to currentDomain
        storename = False
        domain = self.domain if self.domain else self.site.currentDomain
        if self.site.multidomain and domain and domain != self.site.rootDomain:
            storename = domain
        with self.site.db.tempEnv(storename=storename):
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
        # Use explicit domain if set, otherwise fall back to currentDomain
        storename = False
        domain = self.domain if self.domain else self.site.currentDomain
        if self.site.multidomain and domain and domain != self.site.rootDomain:
            storename = domain
        with self.site.db.tempEnv(storename=storename):
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
        parameters_bag = Bag(service_record.get('parameters'))
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

        Retrieves parameters from storage_params registry and uses ServiceHandler
        to get/create the actual storage service instance.

        All storage services are pre-loaded at initialization and kept in sync
        via database triggers (onInserted, onUpdated, onDeleted).

        If storage_name is not found in storage_params, falls back to legacy
        behavior: creates a local storage with storage_name as subdirectory
        of site_static_dir.

        Args:
            storage_name: Name of the storage service
            **kwargs: Additional arguments to override stored parameters

        Returns:
            Storage service instance
        """
        stored_params = self.getStorageParameters(storage_name)
        if not stored_params:
            volume_path = expandpath(os.path.join(self.site.site_static_dir, storage_name))
            return self.site.getService(
                service_type='storage',
                service_name=storage_name,
                implementation='local',
                base_path=volume_path
            )
        service_params = dict(stored_params)
        service_params.pop('service_name', None)
        service_params.update(kwargs)
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



