# Support for Storage Services with Dynamic Path Resolution

## Summary
genro-storage cannot handle Genropy storage services like `rsrc` and `pkg` that require dynamic path resolution based on runtime configuration dictionaries (`site.resources`, `site.packages`). This forces delegation to legacy handlers.

## Problem Description

Genropy has storage services that use two-level path resolution:

### `rsrc` (Resources)
- Format: `rsrc:resource_id/path/to/file`
- `resource_id` must be looked up in `site.resources` dict
- Example: `rsrc:common/images/logo.png` → `site.resources['common']` + `/images/logo.png`

### `pkg` (Package Resources)
- Format: `pkg:package_name/path/to/file`
- `package_name` resolved via `site.packages` dict
- Example: `pkg:gnrcore/pwa/conf.xml` → `site.packages['gnrcore']` + `/pwa/conf.xml`

The first path component is not a filesystem path but a **lookup key** in a runtime dictionary.

## Current Workaround

We skip these services in mount configuration and delegate to legacy handlers:

```python
# Skip in mount config (lines 1213-1216)
if service_name in ('gnr', 'dojo', 'rsrc', 'pkg'):
    logger.debug(f"Skipping {service_name} (handled by StaticHandler)")
    continue

# Delegate in makeNode() (lines 1474-1481)
if not self.storage_manager.has_mount(service_name):
    if service_name in ('gnr', 'dojo', 'rsrc', 'pkg'):
        legacy_handler = LegacyStorageHandler(self.site)
        return legacy_handler.makeNode(*args, **kwargs)
```

This creates inconsistent behavior where some storages use genro-storage and others use legacy code.

## Use Cases in Genropy

- PWA config: `rsrc:pkg_{package}/pwa/conf.xml` (gnrpwahandler.py:41)
- PDF.js viewer: `rsrc:js_libs/pdfjs/web/viewer.html`
- Package assets: `pkg:gnrcore/images/icons.png`

## Proposed Solution

Add **path resolver callbacks** to mount configuration:

```python
def resolve_rsrc_path(resource_id, *path_parts):
    """Called for each access to resolve the base path"""
    base = site.resources.get(resource_id)
    if not base:
        raise ValueError(f"Unknown resource_id: {resource_id}")
    return os.path.join(base, *path_parts)

manager.configure([
    {
        'name': 'rsrc',
        'type': 'local',
        'path_resolver': resolve_rsrc_path  # Called per-access
    }
])

# Access: rsrc:common/images/logo.png
# Calls: resolve_rsrc_path('common', 'images', 'logo.png')
# Returns: /actual/path/to/common/images/logo.png
```

### Key Requirements

1. **Per-access resolution**: The resolver is called for each file access (not just at mount time)
2. **First component is special**: Split path at `/`, first part is the lookup key, rest is the relative path
3. **Dynamic lookup**: The `site.resources` dict can change at runtime

## Expected Behavior

After implementation:
- All Genropy storage services use genro-storage unified API
- No legacy handler delegation needed
- Consistent error handling across all storages

## References

- Workaround: `gnrstoragehandler.py` lines 1213-1216, 1474-1481
- Legacy implementation: `gnrstatichandler.py` RsrcStaticHandler.path() (line 270-273)
- Usage: `gnrpwahandler.py` line 41
