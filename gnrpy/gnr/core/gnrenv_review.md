# gnrenv.py — Review

## Summary

This module defines default paths for Genro framework directories by reading
environment variables and falling back to platform-specific defaults.

## Why no split

- Only 22 lines of code (now ~50 with docstring and type hints)
- Single responsibility: define path constants
- All code is tightly interdependent (paths depend on `_GNRHOME`)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 50 (including docstring and type hints)
- **Classes**: 0
- **Functions**: 0
- **Constants**: 8 (4 public: `GNRHOME`, `GNRINSTANCES`, `GNRPACKAGES`, `GNRSITES`)

## Dependencies

### This module imports from:
- `os` — path manipulation
- `sys` — platform detection
- `gnr.core.gnrhome` — (optional) platform-specific default path

### Other modules that import this:
- `gnr.tests.core.gnrenv_test` — imports module for existence test only

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 23 | COMPAT | Bare `except` catches too broadly; should use `except Exception` or specific types |

**Note**: The COMPAT issue has been addressed in this refactoring by changing
`except:` to `except Exception:`.

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `GNRHOME` | str constant | DEAD | (none found in codebase) |
| `GNRINSTANCES` | str constant | DEAD | (none found in codebase) |
| `GNRPACKAGES` | str constant | DEAD | (none found in codebase) |
| `GNRSITES` | str constant | DEAD | (none found in codebase) |

## Recommendations

1. **Investigate usage**: The public constants appear to have zero callers in
   the current codebase. They may be used by external code or may be obsolete.
   Consider deprecating if truly unused.

2. **Use `pathlib`**: Modern Python code should prefer `pathlib.Path` over
   `os.path.join`. Consider migrating in a future refactoring.

3. **Remove FIXME**: The comment about win32 testing should be investigated
   and either fixed or the comment removed if no longer relevant.
