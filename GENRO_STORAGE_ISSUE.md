# genro-storage Issue: URL Generation for Local Mounts

## Problem Description

When mounting local filesystem storages in genro-storage, the `.url()` method on BrickStorageNode returns `None` for all files, even when they exist.

## Environment

- Library: genro-storage
- Mount type: local
- Configuration: Path-based mounts with callable path resolution

## Test Case

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

## Expected Behavior

The `.url()` method should return a usable URL for the file, either:
1. A relative path like `/gnr/11/js/gnrbag.js`
2. A file:// URL like `file:///path/to/static/gnr/11/js/gnrbag.js`
3. A configurable base URL + path

## Current Workaround

We have to override the URL generation in our wrapper class to generate URLs in the format our application expects.

## Suggested Solution

Add support for URL generation in local storage backend, possibly through:
- A `base_url` parameter in mount configuration
- A `url_prefix` option
- Or automatic generation of relative URLs based on mount name

## Additional Context

This affects integration with web applications that need to serve static files and need to generate HTML with proper URLs pointing to those files.

---
Date: 2025-11-07
Reported by: Francesco Porcari
Context: Genropy integration with genro-storage
