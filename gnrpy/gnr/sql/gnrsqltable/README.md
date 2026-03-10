# gnrsqltable — SQL Table sub-package

## Overview

This package replaces the former monolithic `gnrsqltable.py` module
(~3 200 lines).  The single `SqlTable` class has been split into focused
**mixin** modules — the same pattern adopted for `gnrsql/` and
`gnrsqlmodel/`.

All public names are re-exported from `__init__.py`, so existing code
continues to work unchanged:

```python
from gnr.sql.gnrsqltable import SqlTable
from gnr.sql.gnrsqltable import GnrSqlSaveException, EXCEPTIONS
```

## Module map

| Module              | Class / content              | Responsibility |
|---------------------|------------------------------|----------------|
| `__init__.py`       | Exceptions, `EXCEPTIONS`, re-exports | Backward-compatible facade |
| `helpers.py`        | `add_sql_comment`, `orm_audit_log`, `RecordUpdater` | Decorators and context manager |
| `columns.py`        | `ColumnsMixin`               | Column access, model properties, variant columns, permissions |
| `query.py`          | `QueryMixin`                 | Core `query()`, WHERE translation, column utilities |
| `record.py`         | `RecordMixin`                | Record building, caching, retrieval, captions, pkey guessing |
| `crud.py`           | `CrudMixin`                  | insert / update / delete, batch, writeRecordCluster |
| `triggers.py`       | `TriggersMixin`              | Trigger hooks, protection guards, validation, counters, events |
| `serialization.py`  | `SerializationMixin`         | JSON/XML import/export, field comparison, aggregation |
| `copy.py`           | `CopyMixin`                  | Copy/paste, duplication, archival |
| `utils.py`          | `UtilsMixin`                 | Pkey generation, cross-DB copy, relation explorer, totalizers, retention |
| `table.py`          | `SqlTable`                   | Assembles all mixins + `GnrObject` |

## Architecture

```
SqlTable(ColumnsMixin, QueryMixin, RecordMixin, CrudMixin,
         TriggersMixin, SerializationMixin, CopyMixin,
         UtilsMixin, GnrObject)
```

Each mixin references `self.db`, `self.model`, `self.pkey` etc. which
are defined in `SqlTable` (via `table.py`).  This is standard mixin
design — the mixin classes are not meant to be instantiated alone.

## Critical points

1. **Circular import avoidance** — `triggers.py` and `table.py` use
   deferred imports (`from gnr.sql.gnrsqltable import EXCEPTIONS`) inside
   methods rather than at module level to avoid import cycles between
   the `__init__` facade and sub-modules.

2. **MRO** — Python's C3 linearisation resolves the mixin order.  The
   order listed in `table.py` is intentional: more specific mixins come
   first, `GnrObject` last as the base.

3. **`__init__.py` is the single source of truth** for exceptions and the
   `EXCEPTIONS` registry.  No sub-module should define exceptions.

4. **Proxy handlers** — `HierarchicalHandler` and `XTDHandler` are
   conditionally attached in `SqlTable.__init__` (not in any mixin).

---

## Summary of issues and oddities found

Each entry corresponds to a `# REVIEW:` marker in the source code.

### table.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 104 | `exception()` — `raise exception` when `EXCEPTIONS.get()` returns `None`: raises `TypeError: exceptions must derive from BaseException` instead of a meaningful error | **Bug** |
| 2 | 109 | `exception()` — bare `except Exception` hides real errors in `recordCaption()` | Code smell |

### columns.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 97 | `getPartitionCondition()` — bare `except Exception` catching column-lookup failures | Code smell |
| 2 | 108 | `partitionParameters` — `list(kw.keys())[0]` assumes non-empty dict; guarded by early return but fragile | Potential bug |

### query.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 102 | `sqlWhereFromBag()` — `self.model.virtual_columns` evaluated for side effect, result discarded | Dead code / Design |

### record.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 121 | `buildrecord()` — bare `except Exception: pass` silently ignores Bag parse errors on dtype `'X'` columns | Code smell |
| 2 | 351 | `restoreUnifiedRecord()` — assumes record has `'__moved_related'` key (no `.get()`) | Potential bug |
| 3 | 361 | `restoreUnifiedRecord()` — hardcodes `record['id']` instead of `record[self.pkey]` | **Bug** |
| 4 | 561 | `extendDefaultValues()` — `f[0].items()` without checking if fetch returned empty results | Potential bug |

### crud.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 267 | `empty()` — passes `truncate=None` literally instead of the `truncate` parameter | **Bug** |

### triggers.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 166 | `diagnostic_errors()` — logs warning on every call when not overridden; noisy in production | Design |
| 2 | 171 | `diagnostic_warnings()` — same issue as above | Design |
| 3 | 203 | `_islocked_delete()` — `_isReadOnly(record) is not False`: `_isReadOnly()` returns `True` or `None`, so `None is not False` is `True` — delete lock check is always truthy when table is not read-only | **Bug** |

### serialization.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 416 | `fieldAggregate()` — `not (False in dd)` is unpythonic; clearer as `all(dd)` | Readability |

### copy.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 157 | `_onCopyExpandMany()` — writes to private `node._value = None` | Design |

### utils.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 362 | `importFromAuxInstance()` — uses `assert` for runtime validation; disabled with `python -O` | Design |
| 2 | 577 | `relationExplorer()` — `attributes = dict(targetcol.attributes)` immediately overwritten by `attributes = dict()` | Dead code |
| 3 | 731 | `defaultRetentionPolicy` — `@property @functools.lru_cache` caches the descriptor, not per-instance results | Potential bug |

---

## Confirmed bugs (to be fixed)

1. **`table.py:104`** — `exception()` does `raise exception` where
   `exception` is `None` (from `EXCEPTIONS.get(key)`).  Should raise
   `KeyError` or `ValueError` with the missing key name.

2. **`crud.py:267`** — `empty(truncate=None)` passes the literal `None`
   to `emptyTable()` instead of the caller's `truncate` argument.

3. **`record.py:361`** — `restoreUnifiedRecord()` hardcodes `record['id']`
   instead of `record[self.pkey]`, breaking tables whose primary key is
   not named `id`.

4. **`triggers.py:203`** — `_islocked_delete()` uses
   `_isReadOnly(record) is not False`.  Since `_isReadOnly()` returns
   `True` or `None` (not `False`), `None is not False` evaluates to
   `True`, making the delete-lock always active for non-read-only tables.

## Verification checklist

```bash
# Import smoke tests
python -c "from gnr.sql.gnrsqltable import SqlTable; print('OK')"
python -c "from gnr.sql.gnrsqltable import GnrSqlSaveException, EXCEPTIONS; print('OK')"

# Full test suite (excluding pre-existing locale failure)
pytest gnrpy/tests/sql/ -x -k "not test_outputMode"

# Flake8
flake8 gnrpy/gnr/sql/gnrsqltable/ --max-line-length=120 --ignore=E501,W503,E402
```
