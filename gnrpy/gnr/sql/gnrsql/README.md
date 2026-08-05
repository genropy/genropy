# gnrsql — GnrSqlDb sub-package

## Overview

This package is the result of splitting the original monolithic `gnrsql.py`
(1 237 lines) into a set of focused mixin modules.  The refactoring was
performed as part of **issue #497** following the same pattern established
by the `gnrsqldata` split (PR #490).

`GnrSqlDb` is assembled from seven mixin classes plus the `GnrObject` base:

```python
class GnrSqlDb(
    ConnectionMixin,   # physical connections and store routing
    EnvMixin,          # thread-local environment, workdate, locale
    ExecuteMixin,      # SQL statement execution
    WriteMixin,        # insert / update / delete
    TransactionMixin,  # commit, rollback, deferred callbacks
    QueryMixin,        # query API and model navigation
    SchemaMixin,       # DDL, dump/restore, data import/export
    GnrObject,         # Genro base class
):
```

All inter-mixin dependencies pass through `self`, so no mixin imports
another mixin directly — circular imports are impossible by design.

The `__init__.py` facade re-exports every public name that the old
`gnrsql.py` exposed, ensuring full backward compatibility.

---

## Module map

| Module | Lines | Contents |
|--------|------:|----------|
| `__init__.py` | 54 | Facade — re-exports all public names |
| `helpers.py` | 328 | Standalone helpers: decorators (`in_triggerstack`, `sql_audit`), exceptions (`GnrSqlException`, `GnrSqlExecException`, `GnrMissedCommitException`), `TempEnv`, `TriggerStack`, `TriggerStackItem`, `DbLocalizer`, `MAIN_CONNECTION_NAME` |
| `db.py` | 321 | Core `GnrSqlDb` class: `__init__`, `adapter`, store properties, `createModel`, `startup`, `localizer` |
| `connections.py` | 175 | `ConnectionMixin`: connection lifecycle, store routing, connection parameters |
| `env.py` | 212 | `EnvMixin`: `currentEnv`, `tempEnv`, `workdate`, `locale`, `updateEnv`, tenant/application schemas |
| `execute.py` | 186 | `ExecuteMixin`: `execute` (with `@sql_audit`), `_multiCursorExecute` |
| `write.py` | 269 | `WriteMixin`: `insert`, `update`, `delete`, `insertMany`, `raw_*`, `_onDbChange`, `notifyDbEvent` |
| `transactions.py` | 279 | `TransactionMixin`: `commit`, `rollback`, deferred callback queues, `dbevents`, db maintenance (`analyze`, `vacuum`, `listen`, `notify`) |
| `query.py` | 423 | `QueryMixin`: `query`, `queryCompile`, `table`, `package`, `packages`, `tablesMasterIndex`, `tableTreeBag`, `relationExplorer`, `colToAs` |
| `schema.py` | 399 | `SchemaMixin`: DDL (`createDb`, `dropDb`, `dropTable`, `dropColumn`), dump/restore, model I/O, data import (`importArchive`, `importXmlData`), migration (`diffOrmToSql`, `syncOrmToSql`) |
| **Total** | **2 646** | |

---

## Dependency graph

```
             db.py  (core, __init__, properties)
                |
    +------+----+----+------+------+
    |      |      |      |      |      |
  env  connections execute write transactions
    |      |      |      |      |      |
    +------+------+------+------+------+
                  |             |
              query          schema
```

All arrows represent `self.*` calls resolved at runtime through the
composed `GnrSqlDb` class — there are no import-time dependencies
between mixin modules.

---

## MRO considerations

`GnrSqlAppDb` (in `gnr.app.gnrapp`) subclasses `GnrSqlDb` and overrides
`insert`, `update`, and `delete`.  Because each method lives in exactly
one mixin (`WriteMixin`), the MRO is unaffected by the split.

---

## REVIEW markers — critical points

Each marker in the code follows the pattern `# REVIEW: <description>`.
Below is the full inventory, grouped by severity.

### Potential bugs

| Module | Line | Issue |
|--------|------|-------|
| `helpers.py` | 70 | `in_triggerstack` does not call `pop()` if `func` raises — the trigger stack grows unboundedly on repeated failures |
| `transactions.py` | 79 | `_pendingExceptions` is never cleared after `commit()` raises — a retry of `commit()` will re-raise the same exceptions |
| `write.py` | 246 | `delete()` with a string `deletable` calls `self.application.checkDeletable()`, but `self.application` can be `None` in standalone mode |
| `schema.py` | 192 | `assert os.path.exists(path)` is stripped when running with `python -O` — should be a proper `FileNotFoundError` |

### Design concerns

| Module | Line | Issue |
|--------|------|-------|
| `helpers.py` | 111 | `sql_audit` extracts the SQL verb via `sql.split(" ")[0]`, which is fragile when the SQL starts with a comment or whitespace |
| `helpers.py` | 149 | `GnrMissedCommitException` inherits from `GnrException` rather than `GnrSqlException` — inconsistent with the other SQL exceptions |
| `helpers.py` | 210 | `TempEnv.__exit__` uses value equality (`==`) to decide whether to restore — fragile with mutable values that may have been modified in place |
| `db.py` | 140 | `read_only` is stored in `__init__` but never enforced — no write method checks it |
| `db.py` | 160 | `_connections` is initialised twice in `__init__` (as `{}` and then overwritten) |
| `connections.py` | 72 | `connectionKey()` has a double fallback on `self.currentEnv` that makes the logic hard to follow |

### Dead / unused code

| Module | Line | Issue |
|--------|------|-------|
| `execute.py` | 129 | `cenv = self.currentEnv` — assigned but never used |

### Resource leaks

| Module | Line | Issue |
|--------|------|-------|
| `execute.py` | 176 | A new `ThreadPool(4)` is created on every `_multiCursorExecute` call and never shut down — threads leak over time |

---

## Test coverage

Measured against the full `gnrpy/tests/sql/` suite (562 tests):

- **Coverage of `gnrsql.py` (before split):** 69 %  (236 lines missing)
- **Coverage after split:** identical — the refactoring is purely structural

Three pre-existing test failures in `test_outputMode` (`f_selection_test.py`)
are unrelated to this refactoring.

---

## Verification checklist

```bash
# Import smoke test
python -c "from gnr.sql.gnrsql import GnrSqlDb, TempEnv, TriggerStack, GnrSqlException"

# GnrSqlAppDb MRO preserved
python -c "from gnr.app.gnrapp import GnrSqlAppDb; print(GnrSqlAppDb.__mro__)"

# Full test suite
cd gnrpy && python -m pytest tests/sql/ -v

# Linter
flake8 gnrpy/gnr/sql/gnrsql/
```
