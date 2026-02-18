# gnrbaseservice.py — Review

## Summary

This module is a backward-compatibility alias that re-exports `GnrBaseService`
from its canonical location in `gnr.lib.services`.

## Why no split

- Only 3 lines of code (now ~10 with docstring)
- Single responsibility: re-export one class
- Already minimal and cohesive
- Splitting would add complexity without benefit

## Structure

- **Lines**: 11 (including docstring)
- **Classes**: 0 (re-exports 1)
- **Functions**: 0
- **Constants**: 0

## Dependencies

### This module imports from:
- `gnr.lib.services` — imports `GnrBaseService`

### Other modules that import this:
- `gnr.web.gnrwsgisite_proxy.gnrservicehandler` — imports `GnrBaseService`

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| — | — | No issues found |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `GnrBaseService` | class (re-export) | USED | `gnr.web.gnrwsgisite_proxy.gnrservicehandler` |

## Recommendations

Consider deprecating this module in favor of direct imports from
`gnr.lib.services`. The current re-export exists only for backward
compatibility. A deprecation warning could be added in a future version.
