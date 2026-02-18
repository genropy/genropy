# gnrdatetime.py — Review

## Summary

This module provides timezone-aware datetime handling with sensible defaults.
It offers a drop-in replacement for the standard ``datetime`` module that
ensures all datetime objects are timezone-aware (UTC by default).

## Why no split

- Only 91 lines of code (now ~165 with enhanced docstrings and type hints)
- Single class with related helper functions
- Already well-designed with clear responsibilities
- Splitting would add complexity without benefit

## Structure

- **Lines**: 165 (including docstrings and type hints)
- **Classes**: 1 (`TZDateTime`)
- **Functions**: 2 (`now`, `utcnow`)
- **Constants**: 7 (re-exports from datetime module)

## Dependencies

### This module imports from:
- `datetime` — standard library datetime module

### Other modules that import this:
- `gnr.tests.core.gnrdatetime_test` — imports for testing

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| — | — | No issues found |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `TZDateTime` | class | USED | tests, module aliases |
| `TZDateTime.now` | classmethod | USED | `now()` helper, tests |
| `TZDateTime.utcnow` | classmethod | USED | `utcnow()` helper, tests |
| `TZDateTime.fromiso` | classmethod | USED | tests |
| `datetime` | alias | USED | provides drop-in compatibility |
| `date` | alias | USED | re-export from datetime |
| `time` | alias | USED | re-export from datetime |
| `timedelta` | alias | USED | re-export from datetime |
| `timezone` | alias | USED | re-export from datetime |
| `tzinfo` | alias | USED | re-export from datetime |
| `now` | function | USED | module-level helper |
| `utcnow` | function | USED | module-level helper |

## Recommendations

1. **Excellent module**: This is a well-designed, cohesive module with clear
   documentation and purpose. No changes needed beyond the type hints added
   in this refactoring.

2. **Good design pattern**: The approach of returning standard `datetime`
   objects from the `TZDateTime` factories prevents the subclass from
   "leaking" into user code, which is a good encapsulation pattern.
