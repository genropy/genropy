"""
structures.py - Data structures and utilities for the SQL migration system
==========================================================================

This module defines the **core data structures** used by the entire
migration system. It provides:

1. **Constants** describing the database object hierarchy (ENTITY_TREE)
   and column metadata keys (COL_JSON_KEYS).

2. **Factory functions** (new_*_item) that create normalized JSON
   dictionaries for each type of database entity: schema, table, column,
   index, relation (foreign key), constraint, extension, event trigger.
   These factories ensure a uniform structure used by both the ORM
   extractor and the DB extractor.

3. **Utility functions** shared across modules: hashing for unique names,
   camelCase-to-snake_case conversion, attribute cleanup, JSON-to-Bag tree
   conversion.

The normalized JSON format has this hierarchical structure::

    root
    └── schemas
        └── <schema_name>
            └── tables
                └── <table_name>
                    ├── columns
                    ├── relations (foreign keys)
                    ├── constraints (UNIQUE, CHECK, etc.)
                    └── indexes

Each entity is a dictionary containing at least:
- ``entity``: the entity type ("schema", "table", "column", etc.)
- ``entity_name``: the identifying name of the entity
- ``attributes``: dictionary of type-specific attributes
"""

import re
import hashlib
import json
from collections import defaultdict

from gnr.core.gnrbag import Bag


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENTITY_TREE = {
    'schemas': {
        'tables': {
            'columns': None,
            'relations': None,
            'constraints': None,
            'indexes': None,
        }
    }
}
"""Tree describing the hierarchy of database objects.

Used by :func:`json_to_tree` to recursively navigate the JSON structure
and convert it into a Bag tree. ``None`` indicates a leaf node (no children).
"""

COL_JSON_KEYS = (
    "dtype", "notnull", "sqldefault", "size",
    "unique", "extra_sql", "generated_expression"
)
"""Column attribute keys preserved in the JSON structure.

Both the ORM extractor and the DB extractor filter column attributes
keeping only these keys, ensuring a homogeneous comparison.
"""

GNR_DTYPE_CONVERTER = {'X': 'T', 'Z': 'T', 'P': 'T'}  # REVIEW: Genropy-specific constant in a module meant to be framework-agnostic
"""Mapping from internal Genropy dtypes to canonical dtypes.

Some Genropy dtypes (X=XML, Z=compressed text, P=pickle) are normalized
to 'T' (text) because at the database level they are all text columns.
"""


# ---------------------------------------------------------------------------
# Factory functions for creating normalized JSON entities
# ---------------------------------------------------------------------------

def new_structure_root(dbname):
    """Create the root structure of the migration JSON.

    This is the top-level container that holds all schemas,
    extensions, and event triggers for the database.

    Args:
        dbname: Name of the database.

    Returns:
        dict: Root structure with keys ``root.schemas``, ``root.extensions``,
        ``root.event_triggers``.
    """
    return {
        'root': {
            'entity': 'db',
            'entity_name': dbname,
            'schemas': {},
            'extensions': {},
            'event_triggers': {}
        }
    }


def new_schema_item(schema_name):
    """Create a JSON item for a database schema.

    In Genropy each package corresponds to a PostgreSQL schema.
    The schema contains the package's tables.

    Args:
        schema_name: Name of the schema (corresponds to the package sqlname).

    Returns:
        dict: Schema item with empty ``tables``.
    """
    return {
        'entity': 'schema',
        'entity_name': schema_name,
        'tables': {},
        'schema_name': schema_name,
    }


def new_extension_item(extension_name):
    """Create a JSON item for a PostgreSQL extension.

    Extensions (e.g. ``uuid-ossp``, ``pg_trgm``) are detected
    automatically from ORM column attributes or extracted from the DB.

    Args:
        extension_name: Name of the PostgreSQL extension.

    Returns:
        dict: Extension item with empty ``attributes``.
    """
    return {
        'entity': 'extension',
        'entity_name': extension_name,
        'attributes': {},
    }


def new_event_trigger_item(event_trigger_name):
    """Create a JSON item for a PostgreSQL event trigger.

    Event triggers are database-level triggers (not table-level)
    that respond to DDL events such as CREATE, ALTER, DROP.

    Args:
        event_trigger_name: Name of the event trigger.

    Returns:
        dict: Event trigger item with empty ``attributes``.
    """
    return {
        'entity': 'event_trigger',
        'entity_name': event_trigger_name,
        'attributes': {},
    }


def new_table_item(schema_name, table_name):
    """Create a JSON item for a database table.

    The item includes empty containers for columns, relations, constraints
    and indexes that will be populated later by the extractors.

    Args:
        schema_name: Name of the containing schema.
        table_name: Name of the table.

    Returns:
        dict: Table item with empty ``columns``, ``relations``, ``constraints``,
        ``indexes`` and ``pkeys`` set to None in attributes.
    """
    return {
        'entity': 'table',
        'entity_name': table_name,
        "attributes": {"pkeys": None},
        "columns": {},
        "relations": {},
        "constraints": {},
        "indexes": {},
        'schema_name': schema_name,
        'table_name': table_name
    }


def new_column_item(schema_name, table_name, column_name, attributes=None):
    """Create a JSON item for a database column.

    Attributes are cleaned via :func:`clean_attributes` to remove
    empty or default values.

    Args:
        schema_name: Name of the schema.
        table_name: Name of the table.
        column_name: Name of the column.
        attributes: Dictionary of attributes (dtype, size, notnull, etc.).

    Returns:
        dict: Column item with cleaned attributes.
    """
    return {
        "entity": "column",
        "entity_name": column_name,
        "attributes": clean_attributes(attributes),
        "schema_name": schema_name,
        "table_name": table_name,
        "column_name": column_name
    }


def new_constraint_item(schema_name, table_name, columns, constraint_type,
                        constraint_name=None):
    """Create a JSON item for a constraint (e.g. multi-column UNIQUE).

    The constraint name is automatically generated via MD5 hash if not
    specified, ensuring uniqueness and determinism.

    Args:
        schema_name: Name of the schema.
        table_name: Name of the table.
        columns: List of columns involved in the constraint.
        constraint_type: Type of constraint (e.g. "UNIQUE", "CHECK").
        constraint_name: Explicit constraint name (optional).

    Returns:
        dict: Constraint item with hashed name.
    """
    hashed_entity_name = hashed_name(
        schema=schema_name, table=table_name,
        columns=columns, obj_type='cst'
    )
    return {
        "entity": "constraint",
        "entity_name": hashed_entity_name,
        "attributes": {
            "columns": columns,
            "constraint_name": constraint_name or hashed_entity_name,
            "constraint_type": constraint_type
        },
        "schema_name": schema_name,
        "table_name": table_name,
    }


def new_relation_item(schema_name, table_name, columns, attributes=None,
                      constraint_name=None):
    """Create a JSON item for a relation (foreign key).

    Relations link columns of one table to columns of another table
    (related_schema.related_table.related_columns). The name is hashed
    for uniqueness.

    Args:
        schema_name: Name of the source table's schema.
        table_name: Name of the source table.
        columns: List of source columns of the FK.
        attributes: Dictionary with related_table, related_schema,
            related_columns, on_delete, on_update, deferrable, etc.
        constraint_name: Explicit FK constraint name (optional).

    Returns:
        dict: Relation item with cleaned attributes and hashed name.
    """
    attributes['columns'] = columns  # REVIEW: mutates caller's dict — should copy first
    hashed_entity_name = hashed_name(
        schema=schema_name, table=table_name,
        columns=columns, obj_type='fk'
    )
    constraint_name = constraint_name or hashed_entity_name
    attributes['constraint_name'] = constraint_name
    return {
        "entity": "relation",
        "entity_name": hashed_entity_name,
        "attributes": clean_attributes(attributes),
        "schema_name": schema_name,
        "table_name": table_name
    }


def new_index_item(schema_name, table_name, columns, attributes=None,
                   index_name=None):
    """Create a JSON item for a database index.

    Indexes can have additional attributes such as method (btree, gin, gist),
    WITH options, tablespace, WHERE condition and per-column sort order.

    Args:
        schema_name: Name of the schema.
        table_name: Name of the table.
        columns: List of indexed columns.
        attributes: Dictionary with method, with_options, tablespace,
            unique, where, columns (dict column->sorting).
        index_name: Explicit index name (optional).

    Returns:
        dict: Index item with cleaned attributes and hashed name.
    """
    hashed_entity_name = hashed_name(
        schema=schema_name, table=table_name,
        columns=columns, obj_type='idx'
    )
    attributes['index_name'] = index_name or hashed_entity_name  # REVIEW: mutates caller's dict — should copy first
    return {
        "entity": "index",
        "entity_name": hashed_entity_name,
        "attributes": clean_attributes(attributes),
        "schema_name": schema_name,
        "table_name": table_name
    }


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def nested_defaultdict():
    """Create a recursively nested defaultdict.

    Used to build tree structures where any intermediate level is
    created automatically on access. For example::

        d = nested_defaultdict()
        d['db']['schemas']['myschema']['tables']['mytable'] = {...}

    Returns:
        defaultdict: A defaultdict that creates other defaultdicts as default.
    """
    return defaultdict(nested_defaultdict)


def camel_to_snake(camel_str):
    """Convert a camelCase string to snake_case.

    Used to normalize ORM relation (joiner) attributes, which arrive
    in camelCase (e.g. ``onDeleteSql`` -> ``on_delete_sql``).

    Args:
        camel_str: String in camelCase format.

    Returns:
        str: String converted to snake_case.
    """
    snake_str = re.sub(r'(?<!^)([A-Z])', r'_\1', camel_str)
    return snake_str.lower()


def json_equal(json1, json2):
    """Compare two JSON structures regardless of element order.

    Serializes both structures with sorted keys and compares the resulting
    strings. Useful for verifying that two structures are semantically
    equivalent even if dictionaries have different ordering.

    Args:
        json1: First JSON structure (dict/list).
        json2: Second JSON structure (dict/list).

    Returns:
        bool: True if the structures are equivalent.
    """
    json1_str = json.dumps(json1, sort_keys=True)
    json2_str = json.dumps(json2, sort_keys=True)
    return json1_str == json2_str


def json_to_tree(data, key, entity_tree=None, parent=None):  # REVIEW: Genropy-specific (uses Bag) in a module meant to be framework-agnostic
    """Convert a flat JSON structure into a hierarchical Bag tree.

    Recursively navigates the JSON structure following the hierarchy defined
    in ``entity_tree`` (default: ENTITY_TREE) and builds a Bag tree
    where each node has ``name`` and ``entity`` attributes.

    This function is used by ``SqlMigrator.jsonModelWithoutMeta()`` to
    create a UI-navigable representation of the ORM and SQL structures.

    Args:
        data: JSON dictionary containing the entities.
        key: Current key to process (e.g. "schemas", "tables").
        entity_tree: Navigation tree (default ENTITY_TREE).
        parent: Parent Bag to append nodes to (None = create new Bag).

    Returns:
        Bag: Bag tree with the database structure.
    """
    if parent is None:
        parent = Bag()
    if not data:
        return parent
    entity_tree = entity_tree or ENTITY_TREE
    entities = data[key]
    for entity_item in entities.values():
        content = Bag()
        parent.addItem(
            entity_item['entity_name'], content,
            name=entity_item['entity_name'],
            entity=entity_item['entity'],
            _attributes=entity_item.get('attributes', {})
        )
        if not entity_tree[key]:
            continue
        children_keys = list(entity_tree[key].keys())
        single_children = len(children_keys) == 1
        for childname in children_keys:
            collections = content
            if not single_children:
                collections = Bag()
                content.addItem(childname, collections, name=childname)
            json_to_tree(
                data[key][entity_item['entity_name']],
                key=childname,
                entity_tree=entity_tree[key],
                parent=collections
            )
    return parent


def clean_attributes(attributes):
    """Remove attributes with empty, None, False or default values.

    This function normalizes attribute dictionaries by removing keys
    whose value is considered "empty" or irrelevant for comparison:
    None, empty dict, False, empty list, empty string, "NO ACTION"
    (which is the default for on_delete/on_update in FK).

    Args:
        attributes: Dictionary of attributes to clean.

    Returns:
        dict: Dictionary with only significant attributes.
    """
    return {
        k: v for k, v in attributes.items()
        if v not in (None, {}, False, [], '', "NO ACTION")
    }


def hashed_name(schema, table, columns, obj_type='idx'):
    """Generate a unique and deterministic name for constraints or indexes.

    Combines schema, table, columns and type into an identifying string,
    computes its MD5 hash and uses the first 8 characters as suffix.
    This ensures short, unique and time-stable names.

    The resulting format is ``{obj_type}_{hash8}``, for example:
    - ``idx_a3f2c1b0`` for an index
    - ``fk_7e4d9a12`` for a foreign key
    - ``cst_b5c8e3f1`` for a constraint

    Args:
        schema: Name of the schema.
        table: Name of the table.
        columns: List of columns involved.
        obj_type: Object type ('idx' for index, 'fk' for foreign key,
            'cst' for generic constraint).

    Returns:
        str: Unique name in the format ``{type}_{hash8}``.
    """
    columns_str = "_".join(columns)
    identifier = f"{schema}_{table}_{columns_str}_{obj_type}"
    hash_suffix = hashlib.md5(identifier.encode()).hexdigest()[:8]  # REVIEW: 8 hex chars = 32 bits — collision probable at ~65k items (birthday paradox)
    return f"{obj_type}_{hash_suffix}"
