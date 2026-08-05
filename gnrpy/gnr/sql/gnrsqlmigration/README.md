# SQL Migration Package — Architecture and Structure Reference

## Overview

This package implements a **schema migration system** that compares an ORM model
against a live database and generates the SQL commands needed to bring the database
in sync with the ORM.

The system is built around a **normalized JSON structure** that acts as a
database-agnostic contract between three actors:

1. **ORM Extractor** — reads the application model and produces the JSON
2. **DB Extractor** — reads the actual database and produces the same JSON
3. **Diff Engine + Command Builder** — compares the two JSONs and generates SQL

Because both extractors produce the same format, the diff engine does not need
to know anything about ORM internals or database-specific catalogs.

---

## The Normalized JSON Structure

### Design principles

- Every object is an **entity** with `entity`, `entity_name` and `attributes`
- The hierarchy is navigable via nested dictionaries
- Names of constraints, indexes and FKs are **hashed** for deterministic comparison
- Attributes are **cleaned** (no None, no False, no empty values) to avoid spurious diffs

### Current hierarchy

```
root
├── entity: "db"
├── entity_name: <database_name>
├── schemas: {<schema_name>: <schema_item>}
├── extensions: {<ext_name>: <extension_item>}
└── event_triggers: {<trigger_name>: <event_trigger_item>}

schema_item
├── entity: "schema"
├── entity_name: <schema_name>
└── tables: {<table_name>: <table_item>}

table_item
├── entity: "table"
├── entity_name: <table_name>
├── attributes: {pkeys: "col1,col2" | None}
├── columns: {<col_name>: <column_item>}
├── relations: {<hashed_fk_name>: <relation_item>}
├── constraints: {<hashed_cst_name>: <constraint_item>}
└── indexes: {<hashed_idx_name>: <index_item>}

column_item
├── entity: "column"
├── entity_name: <column_name>
└── attributes:
    ├── dtype: str          — normalized data type (T, I, N, R, D, H, B, etc.)
    ├── size: str|None      — "100", "10,2", "0:200"
    ├── notnull: bool|"_auto_" — True, or "_auto_" for PK columns
    ├── sqldefault: str|None — SQL DEFAULT expression
    ├── unique: bool|None
    ├── extra_sql: str|None — extra SQL appended to column definition
    └── generated_expression: str|None — GENERATED ALWAYS AS expression

relation_item (foreign key)
├── entity: "relation"
├── entity_name: <hashed_name>
└── attributes:
    ├── columns: [str]         — source columns
    ├── related_table: str     — target table name
    ├── related_schema: str    — target schema name
    ├── related_columns: [str] — target columns
    ├── constraint_name: str   — actual constraint name
    ├── constraint_type: "FOREIGN KEY"
    ├── on_delete: str|None    — RESTRICT, CASCADE, SET NULL, SET DEFAULT, NO ACTION
    ├── on_update: str|None
    ├── deferrable: bool|None
    └── initially_deferred: bool|None

constraint_item
├── entity: "constraint"
├── entity_name: <hashed_name>
└── attributes:
    ├── columns: [str]
    ├── constraint_name: str
    └── constraint_type: "UNIQUE"|"CHECK"

index_item
├── entity: "index"
├── entity_name: <hashed_name>
└── attributes:
    ├── columns: {col_name: sort_order|None}
    ├── index_name: str
    ├── method: str|None       — btree, gin, gist, brin, hash
    ├── with_options: dict|None
    ├── tablespace: str|None
    ├── unique: bool|None
    └── where: str|None        — partial index condition

extension_item
├── entity: "extension"
├── entity_name: <extension_name>
└── attributes: {}

event_trigger_item
├── entity: "event_trigger"
├── entity_name: <trigger_name>
└── attributes: {<event_trigger_specific_attrs>}
```

### Attribute filtering

Column attributes are filtered through `COL_JSON_KEYS` to ensure only
comparable attributes are kept. Both extractors apply the same filter,
guaranteeing that the diff engine sees homogeneous data.

### Name hashing

Constraints, foreign keys and indexes use deterministic hashed names
(`{type}_{md5_8chars}`) computed from schema + table + columns + type.
This allows the diff engine to match entities across ORM and DB
regardless of the actual constraint name in the database.

---

## Extensibility

The architecture is designed for extension. Adding a new entity type requires:

1. **A factory function** in `structures.py` (e.g. `new_function_item()`)
2. **Extraction logic** in the ORM and/or DB extractor
3. **Handler methods** in the command builder (`added_<entity>`, `changed_<entity>`, `removed_<entity>`)
4. **An entry in `ENTITY_TREE`** if the entity is part of the navigable hierarchy

The diff engine and executor work generically and require no changes.

### Planned entity types

The following entities are not yet implemented but the structure naturally
accommodates them. Each would follow the same `entity`/`entity_name`/`attributes`
pattern.

#### Functions and procedures (schema-level)

```
schema_item
└── functions: {<func_name>: <function_item>}

function_item
├── entity: "function"
├── entity_name: <function_name>
└── attributes:
    ├── language: str          — plpgsql, sql, python, etc.
    ├── return_type: str
    ├── arguments: str         — full argument signature
    ├── body: str              — function body (hash for comparison)
    ├── volatility: str        — VOLATILE, STABLE, IMMUTABLE
    ├── security: str|None     — SECURITY DEFINER | INVOKER
    └── is_procedure: bool     — True for PROCEDURE, False for FUNCTION
```

**ORM counterpart needed**: a way to declare functions in the Genropy model,
possibly via a `@sql_function` decorator or a `functions` section in the
package/table model.

#### Views and materialized views (schema-level)

```
schema_item
└── views: {<view_name>: <view_item>}

view_item
├── entity: "view"
├── entity_name: <view_name>
└── attributes:
    ├── definition: str        — SELECT query (hash for comparison)
    ├── materialized: bool     — True for MATERIALIZED VIEW
    ├── columns: [str]         — output column names
    └── with_data: bool|None   — WITH DATA for materialized views
```

**ORM counterpart needed**: a `views` section in the package model with
the SQL definition as a string or callable.

#### Table triggers (table-level)

```
table_item
└── triggers: {<trigger_name>: <trigger_item>}

trigger_item
├── entity: "trigger"
├── entity_name: <trigger_name>
└── attributes:
    ├── timing: str            — BEFORE, AFTER, INSTEAD OF
    ├── events: [str]          — [INSERT, UPDATE, DELETE, TRUNCATE]
    ├── for_each: str          — ROW | STATEMENT
    ├── function_name: str     — function to execute
    ├── function_schema: str
    ├── condition: str|None    — WHEN clause
    └── arguments: str|None    — arguments passed to the function
```

**ORM counterpart needed**: a trigger declaration in the table model,
referencing a function entity.

#### Custom types (schema-level)

```
schema_item
└── types: {<type_name>: <type_item>}

type_item
├── entity: "type"
├── entity_name: <type_name>
└── attributes:
    ├── type_kind: str         — ENUM, COMPOSITE, DOMAIN, RANGE
    ├── enum_values: [str]|None — for ENUM types
    ├── columns: dict|None     — for COMPOSITE types {name: type}
    ├── base_type: str|None    — for DOMAIN types
    └── constraint: str|None   — for DOMAIN types (CHECK)
```

**ORM counterpart needed**: a `types` section in the package model.
ENUM types are the most common use case.

#### Sequences (schema-level)

```
schema_item
└── sequences: {<seq_name>: <sequence_item>}

sequence_item
├── entity: "sequence"
├── entity_name: <sequence_name>
└── attributes:
    ├── start_value: int
    ├── increment: int
    ├── min_value: int|None
    ├── max_value: int|None
    ├── cycle: bool
    └── owned_by: str|None     — schema.table.column
```

**Note**: serial columns and GENERATED AS IDENTITY implicitly create
sequences. Only standalone sequences (not tied to a column) need this.

### Entity types that probably don't need migration

These are typically managed outside the schema migration workflow:

- **Permissions (GRANT/REVOKE)** — managed by deployment/ops tooling
- **Tablespaces** — infrastructure-level, not schema-level
- **Publications/Subscriptions** — logical replication configuration
- **Foreign Data Wrappers** — external data source configuration
- **Collations** — rarely changed after DB creation

---

## Improvements to current code

### CHECK constraints

The `constraint_item` already has `constraint_type: "CHECK"` and the factory
accepts a `check_clause` parameter, but `process_constraints` in `db_extractor.py`
silently ignores CHECK constraints. Implementation steps:

1. In `db_extractor.py`, process CHECK constraints like UNIQUE constraints
2. Add `check_clause` to the constraint attributes
3. In `command_builder.py`, handle CHECK in `added_constraint` and `changed_constraint`
4. In the ORM, allow declaring CHECK constraints on tables

### Column comments (COMMENT ON)

Database comments are useful for documentation and can be extracted from
`pg_catalog.pg_description`. They could be stored as an additional column
attribute:

```python
COL_JSON_KEYS = (
    "dtype", "notnull", "sqldefault", "size",
    "unique", "extra_sql", "generated_expression",
    "comment"  # <-- new
)
```

The command builder would generate `COMMENT ON COLUMN schema.table.column IS '...'`
for added/changed comments.

**ORM counterpart**: the column `doc` attribute in Genropy could map to this.

### Table comments

Similarly, table-level comments could be an attribute of `table_item`:

```python
table_item["attributes"]["comment"] = "Description of the table"
```

### ENTITY_TREE extension

The current `ENTITY_TREE` only describes the navigable hierarchy for the
`json_to_tree` UI function. When new entity types are added, it needs
to be updated:

```python
ENTITY_TREE = {
    'schemas': {
        'tables': {
            'columns': None,
            'relations': None,
            'constraints': None,
            'indexes': None,
            'triggers': None,      # future
        },
        'views': None,             # future
        'functions': None,         # future
        'types': None,             # future
        'sequences': None,         # future
    }
}
```

### Validation

Currently there is no validation of the JSON structure. A `validate_structure()`
function could verify that:

- Every entity has `entity`, `entity_name` and `attributes`
- Column dtypes are in the known set
- FK targets exist in the structure
- Hashed names are consistent

This would help catch bugs in custom extractors (especially for the standalone
`genro-sqlmigration` package where third-party extractors may produce the JSON).

---

## Summary of issues and oddities found

Each entry corresponds to a `# REVIEW:` marker in the source code.

### structures.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 77 | `GNR_DTYPE_CONVERTER` — Genropy-specific constant in a module meant to be framework-agnostic | Design |
| 2 | 276 | `new_relation_item()` — mutates the `attributes` dict passed by the caller | **Bug** |
| 3 | 314 | `new_index_item()` — mutates the `attributes` dict passed by the caller | **Bug** |
| 4 | 378 | `json_to_tree()` — Genropy-specific function (uses `Bag`) in a module meant to be framework-agnostic | Design |
| 5 | 473 | `hashed_name()` — MD5 with 8 hex chars = 32 bits; collision probable at ~65k items (birthday paradox) | Design |

### orm_extractor.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 250 | `fill_json_relations_and_indexes()` — `indexed = indexed or True` always evaluates to `True`; original value from `colattr` is discarded | Code smell |
| 2 | 330 | `statement_converter()` — returns `None` implicitly for unknown commands; silent data loss | Potential bug |

### db_extractor.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 91 | `class DbExtractor(object)` — old-style `(object)` base class, unnecessary in Python 3 | Code smell |
| 2 | 162 | `prepare_json_struct()` — `infodict is False` comparison; `{}` is also falsy, but the intent is to distinguish "DB doesn't exist" from "empty result" | Potential bug |
| 3 | 318 | `process_constraints()` — `constraint_name=v['constraint_name']` uses stale loop variable `v`; should be `multiple_unique_const['constraint_name']` | **Bug** |
| 4 | 389 | `process_extensions()` — `extension_dict` reassigned to cleaned version; original info lost before storing in `json_meta` | Code smell |

### diff_engine.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 157 | `dictDifferChanges()` — `dict(difflist)` assumes items are 2-tuples; crashes with no context on unexpected format | Potential bug |
| 2 | 160 | `dictDifferChanges()` — `collection.get('entity_name')` wrapping: falsy `entity_name` (empty string) skips wrapping incorrectly | Potential bug |

### command_builder.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 263 | `added_constraint()` — passes `schema_name`/`table_name` to `struct_constraint_sql()` which may not expect them | Design |
| 2 | 598 | `_apply_type_conversion()` — `_conversion_backups` initialized via `hasattr` check instead of in `__init__` | Code smell |
| 3 | 741 | `changed_constraint()` — `constraints_dict['constraint_name']` reads from command dict instead of `constraint_attr['constraint_name']` | **Bug** |

### executor.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 279 | `verifyConversionBackups()` — `self.db.execute()` instead of `self.db.adapter.execute()` — inconsistent API usage | Potential bug |
| 2 | 303 | `verifyConversionBackups()` — bare `except Exception` catches everything; should narrow to specific DB exceptions | Code smell |

### migrator.py

| # | Line | Issue | Severity |
|---|------|-------|----------|
| 1 | 149 | `__init__()` — `self.commands = {}` immediately overwritten by `nested_defaultdict()` in `prepareMigrationCommands()` | Dead code |
| 2 | 254 | `jsonModelWithoutMeta()` — `not (self.sqlStructure or self.ormStructure)`: `{}` is falsy, so re-extracts even when structures were prepared but DB is empty | **Bug** |

---

## Confirmed bugs (to be fixed)

1. **`structures.py:276`** — `new_relation_item()` mutates the caller's
   `attributes` dict by inserting `columns` and `constraint_name` keys.
   Should `dict(attributes)` first.

2. **`structures.py:314`** — `new_index_item()` mutates the caller's
   `attributes` dict by inserting `index_name`.
   Should `dict(attributes)` first.

3. **`db_extractor.py:318`** — `process_constraints()` uses stale loop
   variable `v` instead of `multiple_unique_const` when building
   multi-column UNIQUE constraints. The constraint name from the last
   single-column UNIQUE is used instead of the correct one.

4. **`command_builder.py:741`** — `changed_constraint()` reads
   `constraints_dict['constraint_name']` (from the command dict, which
   is a `nested_defaultdict` — returns an empty defaultdict, never a string)
   instead of `constraint_attr['constraint_name']`.

5. **`migrator.py:254`** — `jsonModelWithoutMeta()` uses
   `not (self.sqlStructure or self.ormStructure)`. When the DB doesn't exist,
   `sqlStructure` is `{}` (falsy), causing unnecessary re-extraction even
   after `prepareStructures()` was called.

## Verification checklist

```bash
# Import smoke tests
python -c "from gnr.sql.gnrsqlmigration import SqlMigrator; print('OK')"
python -c "from gnr.sql.gnrsqlmigration import OrmExtractor, DbExtractor; print('OK')"

# Full test suite
cd gnrpy && python -m pytest tests/sql/ -x -k "not test_outputMode"

# Flake8
flake8 gnrpy/gnr/sql/migration/ --max-line-length=120 --ignore=E501,W503,E402
```

---

## Module summary

| Module | Responsibility |
|---|---|
| `structures.py` | Constants, factory functions, utilities |
| `orm_extractor.py` | ORM model → normalized JSON |
| `db_extractor.py` | Live database → normalized JSON (via adapter) |
| `diff_engine.py` | Compare two JSONs → typed events (added/changed/removed) |
| `command_builder.py` | Events → SQL command fragments |
| `executor.py` | Assemble and execute SQL, verify backups |
| `migrator.py` | Orchestrator composing all components |
