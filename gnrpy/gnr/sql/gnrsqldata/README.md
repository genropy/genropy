# gnrsqldata — Genro SQL Data Layer

Package implementing the GenroPy SQL data-access layer:
query compilation, execution, selections, single-record loading, and lazy resolvers.

## Package structure

```
gnrsqldata/
├── __init__.py      # Facade: re-exports all public classes
├── compiler.py      # SQL compiler (query → SQL text)
├── query.py         # Query builder and fetch methods
├── selection.py     # Result-set wrapper (sort, filter, output)
├── record.py        # Single-record loading and resolvers
└── README.md        # This file
```

## Modules and responsibilities

### `compiler.py` — SQL compilation

Contains two classes:

- **`SqlCompiledQuery`**: data-class collecting all parameters needed to
  generate the final SQL text (columns, joins, where, group_by, having,
  order_by, limit, offset, for_update).  The `get_sqltext(db)` method
  delegates to the database adapter to produce native SQL.

- **`SqlQueryCompiler`**: the actual compiler.  Receives a `tblobj`
  (table model), resolves relational paths (`@rel.column`), generates
  JOIN clauses, expands macros (#IN_RANGE, #PERIOD, #BAG, #ENV, #PREF,
  #THIS), handles virtual columns (sql_formula, py_method, select/exists),
  and produces a `SqlCompiledQuery` instance.

  Two entry-points:
  - `compiledQuery()` for multi-row selections
  - `compiledRecordQuery()` for single-record loading

Module-level regex constants:
`COLFINDER`, `RELFINDER`, `COLRELFINDER`, `IN_RANGEFINDER`,
`PERIODFINDER`, `BAGEXPFINDER`, `BAGCOLSEXPFINDER`, `ENVFINDER`,
`PREFFINDER`, `THISFINDER`.

### `query.py` — Query building and execution

- **`SqlDataResolver`**: base `BagResolver` for lazy data-loading.
  Subclassed in applications to populate Bag nodes on-demand.

- **`SqlQuery`**: main user entry-point.  Builds a query from table,
  columns, where, order_by, etc.
  Consumption modes:
  - `selection()` → `SqlSelection` (most common)
  - `fetch()` → list of row dicts
  - `fetchAsDict()`, `fetchAsBag()`, `fetchGrouped()`
  - `fetchPkeys()`, `fetchAsJson()`
  - `count()` → rowcount without loading data
  - `cursor()` / `servercursor()` → raw cursors
  - `test()` → (sql_text, params) for debugging

### `selection.py` — Results and post-processing

- **`SqlSelection`**: wrapper around data extracted by a query.
  Provides:
  - **Multi-format output**: `output(mode)` with mode among `list`,
    `dictlist`, `json`, `pkeylist`, `bag`, `grid`, `fullgrid`,
    `selection`, `records`, `recordlist`, `baglist`, `count`,
    `distinct`, `distinctColumns`, `data`, `generator`, `listItems`,
    `template`, `tabtext`, `html`, `xls`, `xmlgrid`.
  - **Sort**: `sort(*args)` with multi-column and descending support
    (`'col:d'`).
  - **Filter**: `filter(cb)` / `filter()` to filter/restore.
  - **Apply**: `apply(cb)` to modify/remove/explode rows.
  - **Freeze**: filesystem persistence via pickle (`freeze()`,
    `freezeUpdate()`, `frozenSelection()`).
  - **Totalize**: analytical grouping via `AnalyzingBag`.
  - **Iterators**: `__iter__`, `__len__`, various `iter_*` methods.

### `record.py` — Single records and lazy resolvers

- **`SqlRelatedRecordResolver`**: `BagResolver` that loads a related
  record (FK / one-to-one side) on-demand.

- **`SqlRelatedSelectionResolver`**: `BagResolver` that loads a related
  selection (many side) on-demand.

- **`SqlRecord`**: compiles and executes a single-row query.  Produces a
  hierarchical `SqlRecordBag` with lazy resolvers for each relation.
  Output modes: `bag`, `dict`, `json`, `record`, `newrecord`,
  `sample`, `template`.

- **`SqlRecordBag`**: `Bag` subclass with a `save()` method for direct
  insert-or-update.

## Internal dependency graph

```
compiler  ←──  query  ──→  selection
    ↑                          │
    └──────── record ──────────┘
              (uses compiler + is used by selection)
```

- `compiler.py` does not import from other package modules.
- `query.py` imports from `compiler` and `selection`.
- `selection.py` imports from `record`.
- `record.py` imports from `compiler`.

## `__init__.py` — Backward compatibility

The `__init__.py` file re-exports all public classes:

```python
from gnr.sql.gnrsqldata.compiler import SqlCompiledQuery, SqlQueryCompiler
from gnr.sql.gnrsqldata.query import SqlQuery, SqlDataResolver
from gnr.sql.gnrsqldata.selection import SqlSelection
from gnr.sql.gnrsqldata.record import (SqlRecord, SqlRecordBag,
                                        SqlRelatedRecordResolver,
                                        SqlRelatedSelectionResolver)
```

This allows existing code to keep importing from `gnr.sql.gnrsqldata`
without any changes.

---

## Summary of issues and oddities found

Each entry corresponds to a `# REVIEW:` marker in the source code.
Detailed notes are also appended at the end of each module.

### compiler.py

| # | Issue | Severity |
|---|-------|----------|
| 1 | `_getJoinerCnd` — commented-out method, never referenced | Dead code |
| 2 | `_findRelationAlias` — references non-existent `GnrSqlBadRequest` | Refactor |
| 3 | `getFieldAlias` — `FIXME refs #120` block with commented-out code | Dead code |
| 4 | `compiledQuery` — `#raise str(...)` debug leftover | Dead code |
| 5 | `compiledQuery` — comment "It is the right behaviour ????" on distinct/count + exploding | Design |
| 6 | `_handle_virtual_columns` — `else` branch with only `pass`, variables unassigned | Potential bug |
| 7 | `_handle_virtual_columns` — commented-out Python 2 debug print | Dead code |
| 8 | `expandInRange` vs legacy between — inconsistency `<=` vs `<` | Inconsistency |
| 9 | `expandPeriod` — native SQL BETWEEN, consider deprecating in favor of range | Deprecation |
| 10 | `compiledRecordQuery` — duplicated `virtual_columns = ... or []` line | Copy-paste |
| 11 | `_getRelationAlias` — `target_sqlcolumn` potentially `None` | Potential bug |

### query.py

| # | Issue | Severity |
|---|-------|----------|
| 1 | `SqlDataResolver.init()` — commented-out old `get_app` code | Dead code |
| 2 | `setJoinCondition` — commented-out `resolver()` method | Dead code |
| 3 | `fetchAsJson` — `GnrDictRowEncoder` inner class | Refactor |
| 4 | `count()` — variable `l` shadows builtin `len` | Code smell |
| 5 | `handlePyColumns` — commented-out line identical to the next one | Dead code |
| 6 | `_dofetch` — inconsistent multi-cursor handling, `index` potentially unbound | Potential bug |
| 7 | `__init__` — variables `rels` and `params` computed but never used | Dead code |

### selection.py

| # | Issue | Severity |
|---|-------|----------|
| 1 | `__init__` — `_aggregateRows == True` instead of truthiness check | Code smell |
| 2 | `_freezeme` — `analyzeBag != None` instead of `is not None` | Code smell |
| 3 | `_freezeme` — cryptic expression `'frozen' * bool(...)` | Readability |
| 4 | `_freeze_filtered` — opens file as `"w"` instead of `"wb"` for pickle | **BUG** |
| 5 | `extend` — `merge` parameter nearly inert | Design |
| 6 | `append` — docstring declared non-existent parameter `i` | Wrong doc |
| 7 | `remove` — `not(cb)` negates the callable itself, not its result | **BUG** |
| 8 | `out_count` — consumes generator just to count, inefficient | Performance |
| 9 | `out_tabtext` — no handling for `None` (crashes on `.replace()`) | Potential bug |
| 10 | `buildAsBag` — commented-out code block (rowcaptionDecode) | Dead code |
| 11 | `out_xmlgrid` — commented-out XML code blocks | Dead code |

### record.py

| # | Issue | Severity |
|---|-------|----------|
| 1 | `resolverSerialize()` duplicated across two resolver classes | DRY violation |
| 2 | `_set_result` ignores the `result` parameter | Design |
| 3 | `__init__` — truthiness check on `pkey` fails for `pkey=0` | Potential bug |
| 4 | `_loadRecord_DynItemOneOne` — identical `if virtual` branches | Dead code |
| 5 | `#if True or resolver_*:` / `#else:` — old toggle in 3 methods | Dead code |
| 6 | `SqlRecordBag._set_db/_get_db` — commented-out weakref | Refactor |
| 7 | `aggregateRecords` — parameter `index` never used | Signature |
| 8 | `_loadRecord_DynItem*` — parameters `resolver_one`/`resolver_many` unused | Signature |

### Confirmed bugs (to be fixed)

1. **`selection.py: _freeze_filtered`** — `os.fdopen(handle, "w")` should
   be `"wb"` for `pickle.dump`.  On Python 3 this causes `TypeError`.

2. **`selection.py: remove`** — `not(cb)` always returns `False`, so
   `filter(False, data)` always empties the list.  The intent was
   `filter(lambda r: not cb(r), data)`.
