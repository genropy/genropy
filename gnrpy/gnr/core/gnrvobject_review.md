# gnrvobject.py — Review

## Summary

This module provides classes for dealing with vCard objects using the
vobject library. Currently only implements `VCard` class.

## Why no split

- Only 134 lines of code (now ~220 with docstrings and type hints)
- Single class with related constant
- Already minimal and cohesive
- Splitting would add complexity without benefit

## Structure

- **Lines**: 220 (including docstrings and type hints)
- **Classes**: 1 (`VCard`)
- **Functions**: 0
- **Constants**: 1 (`VALID_VCARD_TAGS`)

## Dependencies

### This module imports from:
- `vobject` — vCard/vCal library
- `gnr.core.logger` — logging

### Other modules that import this:
- `gnr.tests.core.gnrvobject_test` — tests

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 215-221 | SMELL | `fillFrom` has redundant if/elif/else branches that all do the same thing |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `VCard` | class | USED | tests only |
| `VCard.__init__` | method | USED | tests |
| `VCard._tag_n` | method | INTERNAL | `setTag` |
| `VCard._tag_adr` | method | INTERNAL | `setTag` |
| `VCard.doserialize` | method | USED | tests |
| `VCard.doprettyprint` | method | DEAD | (none found) |
| `VCard.setTag` | method | INTERNAL | `fillFrom` |
| `VCard.fillFrom` | method | INTERNAL | `__init__` |
| `VALID_VCARD_TAGS` | constant | USED | `setTag` |

## Recommendations

1. **Simplify fillFrom**: The method has redundant branches:
   ```python
   def fillFrom(self, card):
       for tag, v in card.items():
           self.setTag(tag, v)
   ```

2. **Add vCal support**: The module docstring mentions vCal but no
   implementation exists. Either implement it or remove the reference.

3. **Investigate usage**: The `VCard` class is only used in tests.
   It may be used by external code or may be a candidate for deprecation.
