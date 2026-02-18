# gnrsys.py — Review

## Summary

This module provides utility functions for interacting with the operating
system and filesystem, including path manipulation, directory creation,
and progress display.

## Why no split

- Only 113 lines of code (now ~180 with docstrings and type hints)
- All functions are related (OS/filesystem utilities)
- Functions are small and independent
- Splitting would add complexity without benefit

## Structure

- **Lines**: 180 (including docstrings and type hints)
- **Classes**: 0
- **Functions**: 5 (`progress`, `mkdir`, `expandpath`, `listdirs`, `resolvegenropypath`)
- **Constants**: 0

## Dependencies

### This module imports from:
- `os` — filesystem operations
- `sys` — stdout for progress display

### Other modules that import this:
- `gnr.app.gnrapp` — imports `expandpath`
- `gnr.app.gnrdeploy` — imports `expandpath`
- `gnr.app.cli.gnrdbsetup` — imports `expandpath`
- `gnr.app.cli.gnrdbsetupparallel` — imports `expandpath`
- `gnr.app.cli.gnrheartbeat` — imports `expandpath`
- `gnr.app.cli.gnrmkapachesite` — imports `expandpath`
- `gnr.app.cli.gnrremotebagserve` — imports `expandpath`
- `gnr.core.gnrconfig` — imports `expandpath`
- `gnr.core.gnrhtml` — imports `expandpath`
- `gnr.db.cli.gnrmigrate` — imports `expandpath`
- `gnr.dev.cli.gnraddprojectrepo` — imports `expandpath`
- `gnr.lib.services.storage` — imports `expandpath`
- `gnr.web.gnrwsgisite` — imports `expandpath`
- `gnr.web.gnrdaemonhandler` — imports `expandpath`
- `gnr.web.cli.gnrsyncstorage` — imports `expandpath`
- `gnr.web.gnrwsgisite_proxy.gnrresourceloader` — imports `expandpath`
- `gnr.web.gnrwsgisite_proxy.gnrstatichandler` — imports `expandpath`
- `gnr.web.gnrwsgisite_proxy.gnrstoragehandler` — imports `expandpath`

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 127-136 | BUG | `listdirs` uses `os.walk` incorrectly — os.walk doesn't accept a callback function; the callback is never invoked |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `progress` | function | USED | tests |
| `mkdir` | function | USED | tests |
| `expandpath` | function | USED | 18+ modules across the codebase |
| `listdirs` | function | DEAD | tests only (and broken) |
| `resolvegenropypath` | function | USED | tests only (may have external callers) |

## Recommendations

1. **Fix listdirs**: The `listdirs` function is broken — it tries to pass a
   callback to `os.walk`, but `os.walk` is a generator that doesn't accept
   callbacks. It should be rewritten to use `os.walk` correctly:
   ```python
   def listdirs(path, invisible_files=False):
       files = []
       for root, dirs, names in os.walk(path):
           for name in names:
               if invisible_files or not name.startswith('.'):
                   files.append(os.path.realpath(os.path.join(root, name)))
       return files
   ```

2. **Consider pathlib**: Modern Python code should prefer `pathlib.Path` for
   path manipulation. The `expandpath` function could be simplified using pathlib.
