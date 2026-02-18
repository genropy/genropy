# gnrredbaron.py — Review

## Summary

This module provides utilities for analyzing Python source code using the
RedBaron library. It can parse Python files and convert their structure
to a Bag tree representation.

## Why no split

- Only 64 lines of code (now ~130 with docstrings and type hints)
- Single class with a single responsibility
- Most methods are stubs (not implemented)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 130 (including docstrings and type hints)
- **Classes**: 1 (`GnrRedBaron`)
- **Functions**: 0
- **Constants**: 0

## Dependencies

### This module imports from:
- `redbaron` — `RedBaron` (optional, with fallback)
- `gnr.core.gnrbag` — `Bag`

### Other modules that import this:
- `gnr.web.gnrwebpage_proxy.developer` — commented out import (lines 198, 202)
- `gnr.tests.core.gnrredbaron_test` — imports module for existence test only

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 89-91 | SMELL | `toTreeBag()` was not returning the result Bag. Added `return result`. |
| 95-100 | DEAD | `moduleToTree()` is a stub method, not implemented |
| 107-114 | DEAD | `getModuleElement()` is a stub method, not implemented |
| 120-127 | DEAD | `saveModuleElement()` is a stub method, not implemented |
| 133-136 | DEAD | `__main__` block with hardcoded developer path |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `GnrRedBaron` | class | DEAD | (commented out in `developer.py`) |
| `GnrRedBaron.__init__` | method | DEAD | (none found) |
| `GnrRedBaron.toTreeBag` | method | DEAD | (none found) |
| `GnrRedBaron.moduleToTree` | method | DEAD | stub, not implemented |
| `GnrRedBaron.getModuleElement` | method | DEAD | stub, not implemented |
| `GnrRedBaron.saveModuleElement` | method | DEAD | stub, not implemented |

## Recommendations

1. **Complete or remove**: This class appears to be an abandoned prototype.
   The stub methods should either be implemented or the entire module
   should be deprecated.

2. **Remove hardcoded path**: The `__main__` block contains a hardcoded
   developer path that should be removed or made configurable.

3. **Fix exception type**: Uses generic `Exception` instead of a more
   specific exception type for missing redbaron.

4. **Consider alternatives**: RedBaron is no longer actively maintained.
   Consider using `ast` module or `libcst` for Python code analysis.
