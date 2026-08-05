# gnrsqlmodel — SQL Model Package

Refactored from the monolithic `gnrsqlmodel.py` (2 148 lines) into 7
focused modules plus a facade `__init__.py`.

Ref: issue #498

## Module Map

| Module | Lines | Classes / Functions |
|---|---:|---|
| `helpers.py` | 133 | `bagItemFormula`, `toolFormula`, `NotExistingTableError`, `ConfigureAfterStartError` |
| `obj.py` | 238 | `DbModelObj`, `DbPackageObj` |
| `columns.py` | 358 | `DbBaseColumnObj`, `DbColumnObj`, `DbVirtualColumnObj`, `AliasColumnWrapper` |
| `containers.py` | 157 | `DbTableAliasObj`, `DbColgroupObj`, `DbSubtableObj`, 8 list objects, `DbIndexObj` |
| `resolvers.py` | 252 | `RelationTreeResolver`, `ModelSrcResolver` |
| `table.py` | 902 | `DbTableObj` |
| `model.py` | 1337 | `DbModel`, `DbModelSrc` |
| `__init__.py` | 151 | facade — re-exports all 24 classes + 2 functions + 2 exceptions |
| **Total** | **3 528** | |

## Dependency Graph (compile-time)

```
helpers      ← standalone, no gnrsqlmodel imports
       ↑
obj          ← imports: GnrStructObj, GnrSqlMissingTable
       ↑
columns      ← inherits from DbModelObj
       ↑
containers   ← inherits from DbModelObj
       ↑
resolvers    ← standalone (uses self.dbroot at runtime)
       ↑
table        ← imports: RelationTreeResolver, DbVirtualColumnObj, AliasColumnWrapper
       ↑
model        ← imports: DbVirtualColumnObj, DbIndexObj, DbModelObj, helpers
       ↑
__init__.py          ← imports everything, re-exports, patches __module__
```

No circular imports — strictly bottom-up.

## moduleDict Compatibility

`DbModel.build()` calls:

```python
sqldict = moduleDict('gnr.sql.gnrsqlmodel', 'sqlclass,sqlresolver')
```

This scans `sys.modules['gnr.sql.gnrsqlmodel']` for classes with a
`sqlclass` attribute, filtering by `cls.__module__ == module.__name__`.
Since the classes now live in sub-modules, `__init__.py` patches their
`__module__` to `'gnr.sql.gnrsqlmodel'` so that `moduleDict` continues
to find all 16 classes.

## Class Hierarchy

```
GnrStructObj
└── DbModelObj
    ├── DbPackageObj
    ├── DbTableObj
    ├── DbBaseColumnObj
    │   ├── DbColumnObj
    │   └── DbVirtualColumnObj
    ├── DbTableAliasObj
    ├── DbColgroupObj
    ├── DbSubtableObj
    ├── DbTblAliasListObj
    ├── DbColAliasListObj
    ├── DbColumnListObj
    ├── DbColgroupListObj
    ├── DbSubtableListObj
    ├── DbIndexListObj
    ├── DbPackageListObj
    ├── DbTableListObj
    └── DbIndexObj

GnrStructData
└── DbModelSrc

BagResolver
├── RelationTreeResolver
└── ModelSrcResolver

object
├── DbModel
└── AliasColumnWrapper
```

## REVIEW Markers Inventory

7 markers across 5 files, grouped by severity:

### High — Thread Safety

| File | Line | Issue |
|---|---|---|
| `resolvers.py` | 104 | Lock acquire/release without try/finally — deadlock risk if `_fields()` raises |
| `table.py` | 354 | `virtual_columns` property has side effects and is not thread-safe (race between cache check and write) |

### Medium — Error Handling / Design

| File | Line | Issue |
|---|---|---|
| `model.py` | 234 | `addRelation()` ~170 lines with bare `except Exception` catching everything |
| `model.py` | 1015 | Runtime insertion into compiled model during source-tree building is fragile |
| `columns.py` | 345 | `AliasColumnWrapper.__init__` — `pop('tag')` / `pop('relation_path')` without defaults |

### Low — Configuration / Purity

| File | Line | Issue |
|---|---|---|
| `helpers.py` | 76 | Hardcoded PostgreSQL type map in `bagItemFormula` — breaks on other backends |
| `columns.py` | 98 | `print_width` property getter has side effect (mutates `self.attributes`) |

## Coverage

Before split: **63%** (478 / 1 285 statements missing).

Coverage by area (approximate):

| Area | Coverage |
|---|---|
| `DbVirtualColumnObj` | ~20% |
| `RelationTreeResolver` | ~25% |
| `DbModel` | ~30% |
| `DbBaseColumnObj` | ~40% |
| `DbModelObj` | ~45% |
| `DbModelSrc` | ~50% |
| `DbTableObj` | ~55% |

## Verification Checklist

```bash
# Import smoke test
python -c "from gnr.sql.gnrsqlmodel import DbModel, DbModelSrc, DbTableObj, DbColumnObj"

# moduleDict still works (critical for model.build())
python -c "
from gnr.core.gnrlang import moduleDict
d = moduleDict('gnr.sql.gnrsqlmodel', 'sqlclass,sqlresolver')
assert len(d) == 16
print('OK:', sorted(d.keys()))
"

# External imports preserved
python -c "from gnr.sql.gnrsqlmodel import DbPackageObj, DbModelObj, DbTableListObj"

# Full test suite
cd gnrpy && python -m pytest tests/sql/ -q --tb=short

# Flake8
flake8 gnrpy/gnr/sql/gnrsqlmodel/
```
