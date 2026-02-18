# gnrdecorator.py — Review

## Summary

This module provides decorator utilities for the Genro framework, including
RPC method marking, kwargs extraction, type casting, and deprecation warnings.
It's heavily used throughout the codebase.

## Why no split

- Only 221 lines of code (now ~400 with docstrings and type hints)
- All decorators are related utility functions
- No class hierarchy to split
- Splitting would add complexity without benefit

## Structure

- **Lines**: 400 (including docstrings and type hints)
- **Classes**: 0
- **Functions**: 8 (`metadata`, `autocast`, `public_method`, `websocket_method`,
  `extract_kwargs`, `customizable`, `oncalling`, `oncalled`, `deprecated`)
- **Constants**: 0

## Dependencies

### This module imports from:
- `warnings` — standard library
- `gnr.core.gnrdict` — dictExtract function
- `gnr.core.gnrclasses` — GnrClassCatalog (imported at runtime in autocast)

### Other modules that import this:
- 20+ files across gnrpy, projects, resources, webtools
- Heavily used for @public_method and @extract_kwargs decorators

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| - | - | No significant issues found |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `metadata` | function | USED | various |
| `autocast` | function | USED | RPC endpoints |
| `public_method` | function | USED | many pages/resources |
| `websocket_method` | function | USED | WebSocket endpoints |
| `extract_kwargs` | function | USED | UI builders |
| `customizable` | function | USED | page methods |
| `oncalling` | function | USED | mixins |
| `oncalled` | function | USED | mixins |
| `deprecated` | function | USED | legacy code |

## Recommendations

1. **No changes needed**: This module is well-designed and heavily used.
   The decorators are clean and follow Python conventions.

2. **Consider functools.wraps**: The wrapper functions could use
   `@functools.wraps(func)` to better preserve function metadata,
   though the current approach manually copies __name__, __doc__, etc.
