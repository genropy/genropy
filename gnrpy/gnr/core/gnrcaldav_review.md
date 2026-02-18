# gnrcaldav.py — Review

## Summary

This module provided CalDAV calendar integration using the caldav library.
**It is deprecated** — the first line raises `DeprecationWarning` to prevent
any import.

## Why no split

- Module is deprecated and should be removed
- Only 79 lines of code
- Single class with related test functions
- All code is unreachable due to the raise at module start

## Structure

- **Lines**: 79 (original), ~220 (with docstrings, type hints, unreachable)
- **Classes**: 1 (`CalDavConnection`)
- **Functions**: 4 (`test`, `test1`, `testcal`, `dt`)
- **Constants**: 0

## Dependencies

### This module imports from:
- `datetime` — `datetime`
- `caldav` — CalDAV client library
- `caldav.elements.dav` — DAV elements
- `gnr.core.gnrbag` — `Bag`, `VObjectBag`
- `gnr.core.gnrlang` — `getUuid`

### Other modules that import this:
- **None** — module is deprecated and not imported anywhere

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 1 | DEAD | Entire module is deprecated (raises DeprecationWarning on import) |
| 11 | SECURITY | Hardcoded credentials in `test()` function |
| 35 | SECURITY | Password included in URL (visible in logs, history) |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `CalDavConnection` | class | DEAD | (none — module cannot be imported) |
| `test` | function | DEAD | (none) |
| `test1` | function | DEAD | (none) |
| `testcal` | function | DEAD | (none) |
| `dt` | function | DEAD | (none) |

## Recommendations

1. **Remove the module**: Since it's deprecated and has zero callers, it should
   be removed entirely in a future cleanup.

2. **Security audit**: Before removal, ensure no credentials from the test
   functions have been committed to git history.

3. **If revival is needed**: The CalDAV integration should be rewritten with:
   - No hardcoded credentials
   - Proper authentication handling (not password in URL)
   - Modern Python practices
