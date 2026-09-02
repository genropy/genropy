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
from gnr.core.gnrstring import boolean
from gnr.web import logger

# genro-storage is an optional dependency (the genro_storage extra): with the
# storage/use_genro_storage flag off nothing here is needed.
try:
    from genro_storage import StorageManager
    from gnr.lib.services import storage_genro
except ImportError:
    StorageManager = None
    storage_genro = None


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

    def __init__(self, site, domain=None, storage_params=None):
        """Initialize the storage handler.

        Args:
            site: The GnrWsgiSite instance
            domain: The domain this handler belongs to (for multidomain mode).
                    If None, uses site.currentDomain at query time.
            storage_params: An existing registry to adopt instead of loading
                    one. Two handlers sharing it stay in sync for free, and the
                    sys.service query runs once.
        """
        self.site = site
        self.domain = domain
        if storage_params is not None:
            self.storage_params = storage_params
        else:
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


class GenroStorageHandler(LegacyStorageHandler):
    """Storage handler serving the mappable mounts through genro-storage.

    Only storage() is overridden: which service resolves a mount is the single
    point of variation, so path parsing, node creation and the four StorageNode
    kwargs keep coming from LegacyStorageHandler, and the legacy StorageNode
    keeps sitting on top. A mount genro-storage cannot serve — every symbolic
    one, http, compressed, relative, sftp, vol: and any unknown name — is
    resolved by the legacy service, so with the flag on those keep behaving
    exactly as before.

    IMPLEMENTATION_MAP holds, per legacy implementation, the genro-storage
    protocol and the parameter renames it needs.
    """

    IMPLEMENTATION_MAP = {
        'local': ('local', {'base_path': 'base_path'}),
        'raw': ('local', {}),
        'aws_s3': ('s3', {'bucket': 'bucket',
                          'base_path': 'base_path',
                          'region_name': 'region',
                          'region': 'region',
                          'aws_access_key_id': 'access_key',
                          'access_key': 'access_key',
                          'aws_secret_access_key': 'secret_key',
                          'secret_key': 'secret_key'}),
    }

    def __init__(self, site, domain=None, storage_params=None):
        if StorageManager is None:
            raise RuntimeError(
                "genro-storage is not installed but storage/use_genro_storage "
                "is enabled. Install it with `pip install 'genropy[genro_storage]'` "
                "or drop the flag from siteconfig to keep the legacy handler."
            )
        self.manager = StorageManager()
        self.mount_configs = {}
        self._genro_services = {}
        super().__init__(site, domain=domain, storage_params=storage_params)
        self._configureMounts()

    def _mountConfig(self, service_name, params):
        """Translate one storage_params entry into a genro-storage mount config.

        Returns None when the entry cannot or must not be served by
        genro-storage; the caller then leaves it to the legacy handler.
        """
        implementation = params.get('implementation')
        mapping = self.IMPLEMENTATION_MAP.get(implementation)
        if not mapping:
            return None
        protocol, rename_map = mapping
        mount = {'name': service_name, 'protocol': protocol}
        for src_key, dest_key in rename_map.items():
            if params.get(src_key):
                mount[dest_key] = params[src_key]
        if implementation == 'raw':
            mount['base_path'] = '/'
        if boolean(params.get('readonly')) or boolean(params.get('write_in_local')):
            # No counterpart in genro-storage: serving a readonly mount through
            # a writable backend would silently drop the restriction.
            logger.warning(
                "genro-storage: mount '%s' is readonly; it stays on the legacy handler",
                service_name)
            return None
        if protocol == 'local':
            base_path = mount.get('base_path')
            if not base_path:
                return None
            if not os.path.isdir(base_path):
                # genro-storage's local backend requires an existing directory,
                # the legacy service creates it on first write.
                logger.warning(
                    "genro-storage: skipping mount '%s': base_path '%s' does not "
                    "exist; it stays on the legacy handler", service_name, base_path)
                return None
        if protocol == 's3':
            if not mount.get('bucket'):
                logger.warning(
                    "genro-storage: skipping mount '%s': no bucket; it stays on "
                    "the legacy handler", service_name)
                return None
            if boolean(params.get('custom_endpoint')) and params.get('endpoint_url'):
                mount['endpoint_url'] = params['endpoint_url']
        return mount

    def _configureMounts(self):
        """Register every mappable mount, one at a time.

        genro-storage validates a batch atomically, so a single unusable mount
        would abort the whole registration (genropy/genro-storage#75). One bad
        mount must never stop site startup: it is skipped with a warning and
        served by the legacy handler.
        """
        for service_name, params in self.storage_params.items():
            mount = self._mountConfig(service_name, params)
            if not mount:
                continue
            try:
                self.manager.configure([mount])
            except Exception as exc:
                logger.warning(
                    "genro-storage: skipping mount '%s' (implementation '%s'): %s; "
                    "it stays on the legacy handler",
                    service_name, params.get('implementation'), exc)
                continue
            self.mount_configs[service_name] = mount

    def _dropMount(self, service_name):
        if self.manager.has_mount(service_name):
            self.manager.delete_mount(service_name)
        self.mount_configs.pop(service_name, None)
        self._genro_services.pop(service_name, None)

    def storage(self, storage_name, **kwargs):
        """Return the genro-storage service for a registered mount, the legacy
        one otherwise.

        A call carrying kwargs overrides the stored parameters, which describes
        a service configured on the fly: that stays legacy.
        """
        if kwargs or not self.manager.has_mount(storage_name):
            return super().storage(storage_name, **kwargs)
        service = self._genro_services.get(storage_name)
        if service is None:
            params = self.getStorageParameters(storage_name) or {}
            service = storage_genro.Service(
                parent=self.site,
                manager=self.manager,
                mount_name=storage_name,
                mount_config=self.mount_configs[storage_name],
                expand_paths=params.get('implementation') == 'raw',
                versioned=boolean(params['versioned']) if 'versioned' in params else None,
                tags=params.get('tags'))
            service.service_name = storage_name
            service.service_implementation = params.get('implementation')
            self._genro_services[storage_name] = service
        return service

    def updateStorageParams(self, service_name):
        result = super().updateStorageParams(service_name)
        # Drop before re-reading: an entry that stopped being mappable must stop
        # being served by genro-storage.
        self._dropMount(service_name)
        self._configureMounts()
        return result

    def removeStorageFromCache(self, service_name):
        result = super().removeStorageFromCache(service_name)
        self._dropMount(service_name)
        return result



