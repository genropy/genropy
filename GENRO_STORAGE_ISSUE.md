# genro-storage Integration Issues in Genropy

Comprehensive documentation of issues encountered when integrating genro-storage library into Genropy framework.

---

## Issue 5: S3 Parameter Mapping - Wrong Parameter Names

### Problem Description

The `_adaptStorageParamsToMount()` method was not correctly mapping Genropy's S3 storage parameters to genro-storage's expected parameter names, causing S3 files to be reported as non-existent even though they exist and are accessible.

### Environment

- Storage type: S3 (aws_s3)
- Backend: FsspecBackend
- Configuration source: sys.storage_service database table

### Test Case

**Storage parameters from database:**
```python
{
  "bucket": "teamset",
  "base_path": "thefamily2",
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "region_name": "eu-central-1",
  "implementation": "aws_s3"
}
```

**Problem:**
```python
# Test file that exists on S3
test_path = 'home:ciak_ordine_acquisto/YE_9TlUrNiS_Y32oSIPppw/re-servizi-dal-02092025-al-18102025.pdf'

# Legacy handler
node_legacy = site_legacy.storageNode(test_path)
print(node_legacy.exists)  # True - works!

# New handler (genro-storage)
node_new = site_new.storageNode(test_path)
print(node_new.exists)  # False - PROBLEM!
```

### Root Cause

The `_adaptStorageParamsToMount()` method was looking for parameter names that didn't match the actual database schema:

**Wrong parameter names:**
```python
if 'region' in params:  # Database has 'region_name', not 'region'
    mount_config['region'] = params['region']
if 'access_key' in params:  # Database has 'aws_access_key_id'
    mount_config['key'] = params['access_key']
if 'secret_key' in params:  # Database has 'aws_secret_access_key'
    mount_config['secret'] = params['secret_key']
# Missing: base_path (S3 prefix) was not passed at all!
```

This resulted in genro-storage receiving a mount configuration **without region, credentials, or prefix**:
```python
{
  'name': 'home',
  'type': 's3',
  'bucket': 'teamset'
  # Missing: region, key, secret, prefix
}
```

### Solution

Fixed `_adaptStorageParamsToMount()` at lines 1356-1377 to check for both Genropy's standard parameter names and short names:

```python
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
```

### Result

After the fix:
```python
# Both handlers now work correctly
node_legacy = site_legacy.storageNode(test_path)
print(node_legacy.exists)  # True

node_new = site_new.storageNode(test_path)
print(node_new.exists)  # True - FIXED!
print(node_new.size)  # 94305 bytes
print(len(list(node_new._brick_node.versions)))  # 1 version
```

### Impact

This was a **critical bug** that prevented NewStorageHandler from accessing any S3 storage. Without correct region, credentials, and prefix, genro-storage couldn't:
1. Connect to the correct S3 region
2. Authenticate with AWS
3. Access files under the correct S3 prefix path

The fix enables full S3 functionality including:
- File existence checks
- Content reading
- Version listing (S3 versioning)
- All other S3 operations

### Implementation

**Commit:** `28e567ea9` - fix(storage): correct S3 parameter mapping for genro-storage integration

**Files modified:**
- `gnrpy/gnr/web/gnrwsgisite_proxy/gnrstoragehandler.py` (lines 1356-1377)

**Type:** Core fix (not a workaround)

---

## Issue 6: S3 Version Metadata Key Format Incompatibility

### Problem Description

S3 version metadata is returned with different key naming conventions depending on which storage handler is used, causing code that accesses version information to fail when switching between handlers.

### Environment

- Storage type: S3 (aws_s3) with versioning enabled
- Affected handlers: Both LegacyStorageHandler and NewStorageHandler
- Location: External package code (gnrcore:sys/webpages/ep_table.py)

### Root Cause

**LegacyStorageHandler** uses boto3 directly, which returns AWS S3 API response format with CamelCase keys:
```python
{
  'VersionId': 'abc123...',
  'IsLatest': True,
  'LastModified': datetime(...),
  'ETag': '...',
  'Size': 12345
}
```

**NewStorageHandler** uses genro-storage, which follows Python naming conventions with snake_case keys:
```python
{
  'version_id': 'abc123...',
  'is_latest': True,
  'last_modified': datetime(...),
  'etag': '...',
  'size': 12345
}
```

Code in external packages that directly accesses these keys will fail with `KeyError` when using NewStorageHandler:
```python
# This works with LegacyStorageHandler but fails with NewStorageHandler
localized_date = self.toText(version['LastModified'], dtype='D')
# KeyError: 'LastModified'
```

### Solution (Workaround)

Since we cannot modify genro-storage to change its key format, and we cannot break compatibility with boto3's format, we implemented a **dual format support workaround** in the consuming code.

Modified `_getVersionBag()` in `gnrcore:sys/webpages/ep_table.py` to check both formats using fallback logic:

```python
# Support both formats: CamelCase (legacy boto3) and snake_case (genro-storage)
last_modified = version.get('last_modified') or version.get('LastModified')
version_id = version.get('version_id') or version.get('VersionId')
is_latest = version.get('is_latest') or version.get('IsLatest')
```

This ensures the code works transparently with both handlers without requiring configuration or user intervention.

### Impact

This is a **breaking API change** in genro-storage compared to direct boto3 usage. While snake_case is more Pythonic, it breaks compatibility with existing code that expects AWS API format.

The workaround ensures:
- ✅ Zero breaking changes for end users
- ✅ Transparent compatibility with both handlers
- ✅ Backward compatibility maintained
- ⚠️ Requires similar workarounds in all code that accesses version metadata

### Implementation

**Commit:** `7dc8a4d59` - fix(storage): support both S3 version key formats for compatibility

**Files modified:**
- `projects/gnrcore/packages/sys/webpages/ep_table.py` (lines 141-158)

**Type:** Workaround (required for genro-storage integration)

**Note:** Other packages that access S3 version metadata directly may need similar modifications.

---

## Issue 1: URL Generation Returns None for Local Mounts

### Problem Description

When mounting local filesystem storages in genro-storage, the `.url()` method on BrickStorageNode returns `None` for all files, even when they exist and other properties (mtime, size, etc.) work correctly.

### Environment

- Library: genro-storage
- Mount type: local
- Configuration: Path-based mounts with callable path resolution

### Test Case

```python
from genro_storage import StorageManager

# Create storage manager
manager = StorageManager()

# Configure local mount
manager.configure([{
    'name': 'gnr',
    'type': 'local',
    'path': '/path/to/static/gnr'
}])

# Create node for existing file
node = manager.node('gnr:11/js/gnrbag.js')

# Check existence
print(node.exists)  # True - file exists
print(node.mtime)   # 1762532049.353479 - mtime works

# Try to get URL
print(node.url())  # None - PROBLEM: should return a URL
```

### Expected Behavior

The `.url()` method should return a usable URL for the file, either:
1. A relative path like `/gnr/11/js/gnrbag.js`
2. A file:// URL like `file:///path/to/static/gnr/11/js/gnrbag.js`
3. A configurable base URL + path (most useful for web applications)

### Impact

This is critical for web frameworks that need to:
- Generate HTML with `<script src="...">` tags pointing to JavaScript files
- Create `<link href="...">` tags for stylesheets
- Reference images and other static assets in templates

### Workaround Implemented

We had to override URL generation in our `NewStorageNode` wrapper class with service-specific URL patterns:

```python
def url(self, **kwargs):
    """Generate external URL for this storage node.

    TEMPORARY WORKAROUND: genro-storage's BrickStorageNode.url() returns None for local mounts.
    """
    return self.internal_url(**kwargs)

def internal_url(self, **kwargs):
    """Generate internal URL for this storage node.

    Generates service-specific URLs to match legacy Genropy URL patterns:
    - rsrc: {external_host}/_rsrc/{resource_id}/{path}
    - pkg: {external_host}/_pkg/{package_name}/{path}
    - pages: {external_host}/_pages/{path}
    - other: {external_host}/_storage/{service_name}/{path}
    """
    if not self.parent or not hasattr(self.parent, 'external_host'):
        return self._generate_url_pattern(self.service_name, self._brick_node.path, '')

    external_host = self.parent.external_host.rstrip('/')
    url = self._generate_url_pattern(self.service_name, self._brick_node.path, external_host)

    # Handle nocache parameter by adding mtime
    nocache = kwargs.pop('nocache', None)
    if nocache:
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

    Different storage services use different URL patterns:
    - rsrc, pkg: first path component is resource_id/package_name
    - pages: direct path mapping
    - others: generic /_storage/ pattern
    """
    parts = path.split('/', 1) if path else ['']
    first_component = parts[0]
    rest_path = parts[1] if len(parts) > 1 else ''

    if service_name == 'rsrc':
        url = f'{external_host}/_rsrc/{first_component}'
        if rest_path:
            url = f'{url}/{rest_path}'
    elif service_name == 'pkg':
        url = f'{external_host}/_pkg/{first_component}'
        if rest_path:
            url = f'{url}/{rest_path}'
    elif service_name == 'pages':
        url = f'{external_host}/_pages/{path}'
    else:
        url = f'{external_host}/_storage/{service_name}/{path}'

    return url
```

**Why service-specific patterns are necessary:**

Genropy's legacy static handlers use different URL patterns for different storage types:
- `RsrcStaticHandler` expects: `/_rsrc/{resource_id}/{path}` (gnrstatichandler.py:276)
- `PkgStaticHandler` expects: `/_pkg/{package_name}/{path}` (gnrstatichandler.py:265)
- `PagesStaticHandler` expects: `/_pages/{path}` (gnrstatichandler.py:286)

Using a generic `/_storage/{service_name}/` pattern for all storages resulted in 404 errors because the web server routes are configured to expect these specific patterns.

### Suggested Solution

Add URL generation support to local storage backend through configuration:
- A `base_url` parameter in mount configuration (e.g., `"base_url": "/static"`)
- A `url_prefix` option for path-based URLs
- Or automatic generation of relative URLs based on mount name

---

## Issue 2: Version-Specific Path Management Incompatibility

### Problem Description

genro-storage uses a static `base_path` model where paths are resolved as `base_path + relative_path`. However, Genropy's `GnrStaticHandler` uses a version-as-first-argument pattern where the version is part of the path components, not part of the base path.

### How Genropy Works

For versioned resources (gnr, dojo), Genropy uses version-specific directories:
- `gnr_d11/js/gnrbag.js` (version 11 of Genro)
- `dojo1.11/dojo/dojo.js` (Dojo version 1.11)

The legacy API works like this:
```python
storage('gnr').url('11', 'js', 'gnrbag.js')
# Resolves to: gnr_d11/js/gnrbag.js
```

The version is the FIRST argument, and the handler maps it to the versioned directory.

### genro-storage Model

genro-storage expects:
```python
manager.configure([{
    'name': 'gnr',
    'type': 'local',
    'path': '/path/to/gnr_d11'  # Static base path
}])

node = manager.node('gnr:js/gnrbag.js')  # Relative path without version
```

### The Incompatibility

When we tried to use callable paths to resolve version-specific directories:

```python
def resolve_gnr_path():
    # site.gnr_path = {'11': '/path/to/gnr_d11', '10': '/path/to/gnr_d10'}
    return next(iter(site.gnr_path.values()))  # Returns /path/to/gnr_d11

manager.configure([{
    'name': 'gnr',
    'type': 'local',
    'path': resolve_gnr_path  # Callable
}])
```

But then the path components still include the version:
```python
node = manager.node('gnr:11/js/gnrbag.js')
# Results in: /path/to/gnr_d11/11/js/gnrbag.js
# WRONG: version appears twice (in base path AND in relative path)
```

### Why This Happens

Because our legacy API passes version as first component: `storage('gnr').url('11', 'js', 'file.js')`

This becomes path `11/js/file.js` which is appended to the already-versioned base path.

### Impact

Cannot use genro-storage for version-managed resources without:
1. Changing the legacy API (breaking change)
2. Implementing complex path manipulation to strip version from components
3. Or excluding these storages from genro-storage entirely

### Workaround Required

We had to exclude 'gnr' and 'dojo' from genro-storage mounts and delegate directly to `GnrStaticHandler`:

```python
def storage(self, service_name):
    """Get storage service adapter.

    For gnr/dojo, delegate to GnrStaticHandler which handles version-specific paths.
    """
    if service_name in ('gnr', 'dojo'):
        # These use version-specific directories incompatible with genro-storage
        # Wrap with adapter to provide internal_path() method
        static_handler = self.site.getStatic(service_name)
        return LegacyGnrStaticAdapter(static_handler)

    return LegacyStorageServiceAdapter(self, service_name)
```

Additionally, we had to create `LegacyGnrStaticAdapter` to wrap `GnrStaticHandler` and provide the `internal_path()` method that the storage service API expects:

```python
class LegacyGnrStaticAdapter:
    """Adapter for GnrStaticHandler to provide storage service API.

    GnrStaticHandler has path() method but not internal_path().
    This adapter bridges that gap.
    """

    def __init__(self, static_handler):
        self.static_handler = static_handler

    def url(self, *args, **kwargs):
        """Delegate to static_handler.url()"""
        return self.static_handler.url(*args, **kwargs)

    def kwargs_url(self, *args, **kwargs):
        """Delegate to static_handler.kwargs_url()"""
        return self.static_handler.kwargs_url(*args, **kwargs)

    def path(self, *args, **kwargs):
        """Delegate to static_handler.path()"""
        return self.static_handler.path(*args, **kwargs)

    def internal_path(self, *args, **kwargs):
        """Provide internal_path() by delegating to path()"""
        return self.static_handler.path(*args, **kwargs)

    def mtime(self, *args, **kwargs):
        """Get modification time by getting filesystem path and using os.path.getmtime()"""
        import os
        file_path = self.static_handler.path(*args, **kwargs)
        if not file_path:
            return 0
        try:
            return os.path.getmtime(file_path)
        except (OSError, TypeError):
            return 0
```

**Why this adapter is necessary:**

The legacy code throughout Genropy uses `storage('gnr').internal_path(version, *path_components)` to get filesystem paths. For example:

```python
# In gnrwebpage.py build_arg_dict():
gnr_static_handler = self.site.storage('gnr')
jsfiles = [
    gnr_static_handler.internal_path(self.gnrjsversion, 'js', '%s.js' % f)
    for f in gnrimports
]
```

Without the adapter, this code fails with:
```
AttributeError: 'GnrStaticHandler' object has no attribute 'internal_path'
```

The adapter provides a transparent wrapper that:
1. Exposes all expected storage service methods (url, path, internal_path, kwargs_url)
2. Delegates internal_path() to path() since they're semantically equivalent for GnrStaticHandler
3. Maintains backward compatibility with all existing code that expects storage services to have internal_path()

This is part of the broader adapter pattern required because GnrStaticHandler was designed with a slightly different API than the generic storage service interface.

### Suggested Solution

Consider supporting dynamic path resolution where the mount can transform/validate incoming path components before appending to base_path. For example:

```python
def gnr_path_resolver(base_path, components):
    """Custom resolver that handles version mapping."""
    if components[0] in version_map:
        # First component is version, map it to versioned directory
        base = version_map[components[0]]
        return os.path.join(base, *components[1:])
    return os.path.join(base_path, *components)

manager.configure([{
    'name': 'gnr',
    'type': 'local',
    'path': '/path/to/genropy',
    'path_resolver': gnr_path_resolver
}])
```

---

## Issue 3: Service Adapter Pattern Necessity

### Problem Description

genro-storage's API design uses a different pattern than Genropy's legacy storage API, requiring a complete adapter layer.

### API Differences

**Legacy Genropy API (service-based):**
```python
service = storage('gnr')
url = service.url('11', 'js', 'file.js')
path = service.internal_path('11', 'js', 'file.js')
mtime = service.mtime('11', 'js', 'file.js')
exists = service.exists('11', 'js', 'file.js')
```

**genro-storage API (node-based):**
```python
node = manager.node('gnr:11/js/file.js')
url = node.url()
path = node.path  # or node.internal_path
mtime = node.mtime
exists = node.exists
```

### Why Adapter Was Required

The fundamental difference is:
- **Legacy**: Service object + method calls with path components as arguments
- **genro-storage**: Direct node creation with full path, then property/method access

We couldn't simply replace the service object because:
1. All existing code uses `storage('name').method(*args)` pattern
2. Converting path components to node creation would require changing every call site
3. The version-first pattern (Issue #2) is deeply embedded in the API

### Adapter Implementation Required

We had to create `LegacyStorageServiceAdapter` to bridge these patterns:

```python
class LegacyStorageServiceAdapter:
    """Adapter to provide legacy storage service API on top of genro-storage."""

    def __init__(self, handler, service_name):
        self.handler = handler
        self.service_name = service_name

    def url(self, *args, **kwargs):
        """Legacy API: storage('name').url('path', 'components')"""
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        if not node:
            return None
        return node.url(**kwargs)

    def internal_path(self, *args):
        """Get filesystem path."""
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        if not node:
            return None
        return node.internal_path

    def mtime(self, *args):
        """Get modification time."""
        path = '/'.join(str(arg) for arg in args)
        fullpath = f'{self.service_name}:{path}'
        node = self.handler.storageNode(fullpath)
        if not node or not node.exists:
            return 0  # Return 0 for non-existent (see Issue #4)
        return node.mtime

    # Similar for exists(), size(), isdir(), isfile(), get_item()...
```

### Impact

This adapter layer adds complexity and has maintenance costs:
- Must keep adapter in sync with both APIs
- Performance overhead from object creation
- Potential for subtle bugs in impedance mismatch

### Why This Matters for genro-storage

This suggests that genro-storage's API design may not fit well with service-oriented storage abstractions. Consider whether a dual API could be supported:

1. **Node API** (current): For direct file operations
2. **Service API** (new): For service-oriented access patterns

Example service API:
```python
service = manager.service('gnr')
url = service.url('11/js/file.js')
node = service.node('11/js/file.js')
```

This would make integration with existing service-based systems much easier.

---

## Issue 4: mtime Property Errors on Non-Existent Files

### Problem Description

Accessing the `mtime` property on a BrickStorageNode for a non-existent file raises `FileNotFoundError` instead of returning None or a sentinel value.

### Error

```python
node = manager.node('gnr:nonexistent.js')
print(node.exists)  # False
print(node.mtime)   # FileNotFoundError: Path not found: nonexistent.js
```

### Expected Behavior

For a non-existent file, either:
1. Return `None` to indicate no modification time
2. Return `0` as a sentinel value
3. Return `False` or some other falsy value

This is consistent with how filesystem operations typically work:
```python
import os
os.path.getmtime('nonexistent')  # Raises OSError
os.stat('nonexistent').st_mtime   # Raises OSError

# But checking existence is always safe:
if os.path.exists(path):
    mtime = os.path.getmtime(path)
```

### Impact

Forces users to always check `exists` before accessing `mtime`, even though mtime is a property that seems like it should be safe to access:

```python
# Have to do this:
if node.exists:
    mtime = node.mtime
else:
    mtime = 0

# Instead of just:
mtime = node.mtime or 0
```

### Workaround Required

In our adapter we had to wrap mtime access:

```python
def mtime(self, *args):
    path = '/'.join(str(arg) for arg in args)
    fullpath = f'{self.service_name}:{path}'
    node = self.handler.storageNode(fullpath)
    if not node or not node.exists:
        return 0  # Safe default instead of exception
    return node.mtime
```

### Suggested Solution

Make `mtime` (and similar properties) return None or 0 for non-existent files, or provide a safe alternative like `get_mtime(default=None)`.

---

## Issue 5: Internal Path Access Requires Private API

### Problem Description

To get the resolved filesystem path from a BrickStorageNode, we had to access private attributes and methods.

### What We Need

For local storages, we need the absolute filesystem path to pass to other system functions (stat, open, etc.):

```python
node = manager.node('gnr:js/file.js')
# Need: /absolute/path/to/gnr/js/file.js
```

### What's Available

- `node.path` - Returns relative path like `js/file.js` (not useful)
- `node.local_path()` - Returns context manager, not a string path
- No public API to get the resolved absolute path

### What We Had To Do

Access private backend implementation:

```python
if hasattr(node, '_backend') and hasattr(node._backend, '_resolve_path'):
    absolute_path = node._backend._resolve_path(node._path)
```

This is fragile and will break if internal implementation changes.

### Impact

Cannot reliably get filesystem paths for:
- Passing to external tools
- Custom file processing
- Integration with legacy code expecting file paths

### Workaround Required

```python
@property
def internal_path(self):
    """Returns the internal filesystem path.

    WORKAROUND: Access private _backend API to get resolved path.
    """
    if hasattr(self._brick_node, '_backend'):
        if hasattr(self._brick_node._backend, '_resolve_path'):
            try:
                return self._brick_node._backend._resolve_path(
                    self._brick_node._path
                )
            except:
                pass
    return self._brick_node.path  # Fallback to relative path
```

### Suggested Solution

Add a public `absolute_path` or `resolved_path` property/method:

```python
node = manager.node('gnr:js/file.js')
print(node.resolved_path)  # /absolute/path/to/gnr/js/file.js

# Or for cross-backend compatibility:
print(node.get_path(resolved=True))  # Absolute path for local, relative for remote
```

---

## Summary of Required Workarounds

To integrate genro-storage into Genropy, we had to implement:

1. **Manual URL Generation** - Override url() method to generate URLs since local backend returns None
2. **Complete Service Adapter** - Bridge service-based API to node-based API with full method translations
3. **Version-Specific Storage Exclusion** - Exclude gnr/dojo from genro-storage, delegate to legacy handler
4. **Safe mtime Access** - Wrap mtime property with existence checks to avoid exceptions
5. **Private API Access** - Use private `_backend._resolve_path()` to get filesystem paths

These workarounds add significant complexity and maintenance burden to the integration.

---

## Recommendations for genro-storage

1. **Add URL Generation Support** - Local storage backend should support URL generation via configuration
2. **Support Dynamic Path Resolution** - Allow custom path resolvers for complex mount patterns
3. **Add Service-Oriented API** - Provide optional service-based API alongside node-based API
4. **Safe Property Access** - Make properties like mtime return None/0 for non-existent files instead of raising
5. **Public Path Resolution API** - Add public method to get absolute resolved paths for local storage

These enhancements would make genro-storage much easier to integrate with existing web frameworks and applications.

---

**Date**: 2025-11-10
**Reported by**: Francesco Porcari
**Context**: Genropy framework integration with genro-storage
**genro-storage dependency**: genro-storage (latest version as of 2025-11)
**Repository**: https://github.com/genropy/genropy
