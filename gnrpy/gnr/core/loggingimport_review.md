# loggingimport.py — Review

## Summary

This module provides a Python re-implementation of hierarchical module import
that logs each import. **It is deprecated and should not be used.**

## Why no split

- Only 123 lines of code (now ~245 with docstrings and type hints)
- Single responsibility (import hooking)
- Module is deprecated and should be removed entirely
- Splitting would be counterproductive

## Structure

- **Lines**: 245 (including docstrings and type hints)
- **Classes**: 0
- **Functions**: 7 (`import_hook`, `determine_parent`, `find_head_package`, `load_tail`, `ensure_fromlist`, `import_module`, `reload_hook`)
- **Constants**: 2 (`original_import`, `original_reload`)

## Dependencies

### This module imports from:
- `builtins` — to replace `__import__` and `reload`
- `sys` — for `sys.modules`
- `imp` — **DEPRECATED** module (removed in Python 3.12)

### Other modules that import this:
- **None** — zero callers in the codebase

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 27 | DEAD | Entire module is unused (zero imports in codebase) |
| 34-36 | COMPAT | Uses deprecated `imp` module (removed in Python 3.12) |
| 231-233 | SMELL | Modifies `builtins.__import__` as side effect on import |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `import_hook` | function | DEAD | (none) |
| `determine_parent` | function | DEAD | (none) |
| `find_head_package` | function | DEAD | (none) |
| `load_tail` | function | DEAD | (none) |
| `ensure_fromlist` | function | DEAD | (none) |
| `import_module` | function | DEAD | (none) |
| `reload_hook` | function | DEAD | (none) |
| `original_import` | variable | DEAD | (none) |
| `original_reload` | variable | DEAD | (none) |

## Recommendations

1. **Remove the module**: This module has zero callers and uses deprecated
   APIs. It should be removed entirely rather than maintained.

2. **Historical note**: The module was a learning/debugging tool for
   understanding Python's import system. It's no longer needed.

3. **If similar functionality is needed**: Modern Python provides
   `importlib` for custom import hooks and `sys.meta_path` for
   import customization.
