# gnrnumber.py — Review

## Summary

This module provides utilities for working with Decimal numbers, including
rounding, conversion from floats, percentage calculations, and partitioning
totals according to quotes.

## Why no split

- Only 68 lines of code (now ~165 with docstrings and type hints)
- All functions are tightly related (decimal number operations)
- Functions depend on each other (`decimalRound` is used by others)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 165 (including docstrings and type hints)
- **Classes**: 0
- **Functions**: 4 (`decimalRound`, `floatToDecimal`, `calculateMultiPerc`, `partitionTotals`)
- **Constants**: 0

## Dependencies

### This module imports from:
- `decimal` — `Decimal`, `ROUND_HALF_UP`
- `collections.abc` — `Generator`, `Iterable`

### Other modules that import this:
- `resources/common/tables/_default/html_res/print_gridres.py`
- `resources/common/tables/_default/action/_common/random_records.py`
- `projects/test_invoice/packages/invc/resources/tables/invoice_row/th_invoice_row.py`
- `gnrpy/tests/core/gnrnumber_test.py`

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| — | — | No issues found |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `decimalRound` | function | USED | `print_gridres.py`, `random_records.py`, `th_invoice_row.py`, tests |
| `floatToDecimal` | function | USED | `decimalRound` (internal), tests |
| `calculateMultiPerc` | function | USED | tests only (may have external callers) |
| `partitionTotals` | function | USED | tests only (may have external callers) |

## Recommendations

1. **Good module**: This is a well-designed, cohesive module. No changes needed
   beyond the documentation and type hints added in this refactoring.

2. **Consider adding more rounding functions**: The module could be extended
   with additional rounding utilities if needed (e.g., `decimalCeil`, `decimalFloor`).
