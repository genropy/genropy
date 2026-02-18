# gnrdict.py — Review

## Summary

Dictionary utilities for GenroPy providing specialized dictionary classes
and extraction functions. The module includes an ordered dictionary class
(`GnrDict`) with index-based key access using `#N` syntax, a read-only
union view of multiple dictionaries (`UnionDict`), and a prefix-based
extraction function (`dictExtract`).

## Why no split

This module should NOT be split because:

1. **Lines**: 244 lines (below 300-line threshold for splitting).
2. **Single responsibility**: All classes/functions relate to dictionary
   manipulation utilities.
3. **Tight interdependencies**: `GnrNumericDict` inherits from `GnrDict`.
4. **Small, cohesive API**: Only 5 public names, all related.

Splitting would create unnecessary complexity for a module that is already
well-organized and focused.

## Structure

- **Lines**: 244 → 537 (after type hints and docstrings)
- **Functions**:
  - `dictExtract` (lines 48-78): Extract dict items by key prefix
- **Classes**:
  - `FakeDict` (lines 81-87): Empty dict subclass for type discrimination
  - `UnionDict` (lines 90-152): Read-only union view of multiple dicts
  - `GnrDict` (lines 155-476): Ordered dictionary with `#N` index access
  - `GnrNumericDict` (lines 479-499): GnrDict variant with numeric iteration
- **Constants**: None (only type variables `_KT`, `_VT`)

## Dependencies

### This module imports from:

- `collections.abc` — `Callable`, `Iterable`, `Iterator`, `Mapping`
- `itertools` — `chain`
- `typing` — `Any`, `TypeVar`
- `warnings` — for deprecated method warnings

### Other modules that import this:

| Module | Import |
|--------|--------|
| `gnr.sql.gnrsqlmigration` | `dictExtract` |
| `gnr.core.gnrdecorator` | `dictExtract` |
| `gnr.core.gnrbaghtml` | `dictExtract` |
| `gnr.web.gnrwebpage` | `dictExtract` |
| `gnr.web.gnrbaseclasses` | `dictExtract` |
| `gnr.core.gnrstructures` | `GnrDict` |
| `gnr.sql.gnrsqldata.compiler` | `dictExtract` |
| `gnr.web.batch.btcexport` | `dictExtract` |
| `gnr.web.gnrmenu` | `dictExtract` |
| `gnr.web.serverwsgi` | `dictExtract` |
| `gnr.web.gnrwebpage_proxy.apphandler` | `dictExtract` |
| `gnr.sql.gnrsqltable_proxy.hierarchical` | `dictExtract` |
| `gnr.sql.gnrsqlmodel.table` | `dictExtract` |
| `gnr.web.gnrwebpage_proxy.rpc` | `dictExtract` |
| `gnr.sql.gnrsqlmodel.model` | `dictExtract` |
| `gnr.sql.gnrsqlmodel.containers` | `dictExtract` |
| `gnr.app.gnrdbo` | `dictExtract` |
| `gnr.sql.gnrsqltable.utils` | `dictExtract` |
| `gnr.web.gnrwebstruct` | `dictExtract` |
| `gnr.sql.gnrsqltable.columns` | `dictExtract` |

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 48 | UNUSED | `is_list` parameter in `dictExtract` is never used |
| 81 | DEAD | `FakeDict` class has no external callers (only tests) |
| 90 | DEAD | `UnionDict` class has no external callers |
| 279 | SMELL | `_label_convert` uses bare `except` that catches too much |
| 456 | COMPAT | `__getslice__` deprecated since Python 2 |
| 477 | COMPAT | `__setslice__` deprecated since Python 2 |
| 479 | DEAD | `GnrNumericDict` class has no external callers (only tests) |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `dictExtract` | function | USED | 20 modules across sql, web, core, app |
| `FakeDict` | class | DEAD | tests only |
| `UnionDict` | class | DEAD | none (defined but never imported) |
| `GnrDict` | class | USED | `gnr.core.gnrstructures` |
| `GnrDict.__init__` | method | USED | via class instantiation |
| `GnrDict.__setitem__` | method | USED | via `d[k] = v` syntax |
| `GnrDict.__getitem__` | method | USED | via `d[k]` syntax |
| `GnrDict.__delitem__` | method | USED | via `del d[k]` syntax |
| `GnrDict.__iter__` | method | USED | via iteration |
| `GnrDict.get` | method | USED | standard dict interface |
| `GnrDict.keys` | method | USED | standard dict interface |
| `GnrDict.values` | method | USED | standard dict interface |
| `GnrDict.items` | method | USED | standard dict interface |
| `GnrDict.pop` | method | USED | standard dict interface |
| `GnrDict.clear` | method | USED | standard dict interface |
| `GnrDict.update` | method | USED | standard dict interface |
| `GnrDict.copy` | method | USED | standard dict interface |
| `GnrDict.setdefault` | method | USED | standard dict interface |
| `GnrDict.popitem` | method | INTERNAL | standard dict interface |
| `GnrDict.index` | method | INTERNAL | not found externally |
| `GnrDict.reverse` | method | INTERNAL | not found externally |
| `GnrDict.sort` | method | INTERNAL | not found externally |
| `GnrDict.iteritems` | method | INTERNAL | Python 2 compatibility |
| `GnrDict.iterkeys` | method | INTERNAL | Python 2 compatibility |
| `GnrDict.itervalues` | method | INTERNAL | Python 2 compatibility |
| `GnrDict.__add__` | method | INTERNAL | `+` operator |
| `GnrDict.__sub__` | method | INTERNAL | `-` operator |
| `GnrDict.__getslice__` | method | COMPAT | deprecated Python 2 |
| `GnrDict.__setslice__` | method | COMPAT | deprecated Python 2 |
| `GnrDict._label_convert` | method | INTERNAL | private helper |
| `GnrNumericDict` | class | DEAD | tests only |

## Recommendations

1. **Remove `is_list` parameter**: The parameter in `dictExtract` is unused
   and should be removed (breaking change but no actual usage).

2. **Remove dead classes**: Consider removing `FakeDict`, `UnionDict`, and
   `GnrNumericDict` if they are truly unused. Verify via comprehensive
   codebase search including all projects.

3. **Fix bare except**: In `_label_convert`, replace `except:` with
   `except (AttributeError, IndexError):` for explicit error handling.

4. **Remove Python 2 compatibility**: The `__getslice__` and `__setslice__`
   methods are deprecated and should be removed if Python 2 support is
   no longer required.

5. **Modernize iteration methods**: `iteritems`, `iterkeys`, `itervalues`
   are Python 2 patterns. Consider deprecation warnings if not already
   removed.

6. **Consider standard OrderedDict**: Since Python 3.7+ dicts are ordered
   by default, evaluate whether `GnrDict` still provides sufficient value
   over the standard `dict` type. The `#N` syntax is the main differentiator.

## Type system notes

The type annotations intentionally override some `dict` method signatures
to match the actual GnrDict behavior (e.g., `keys()` returns `list[str]`
instead of `dict_keys`). These are not bugs but design choices that may
trigger type checker warnings. Pyright/mypy strictness may need adjustment
for this module.
