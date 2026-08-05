# -*- coding: utf-8 -*-
"""
gnrsqlmigration - Genropy SQL migration package
================================================

This package contains the SQL migration system, split from the original
monolithic ``gnrsqlmigration.py`` into thematic modules.

Modules
-------

- **structures.py**: Constants, factory functions and shared utilities.
- **orm_extractor.py**: ``OrmExtractor`` — reads the Genropy ORM model.
- **db_extractor.py**: ``DbExtractor`` — queries the actual database.
- **diff_engine.py**: ``DiffMixin`` — compares ORM vs DB structures.
- **command_builder.py**: ``CommandBuilderMixin`` — translates diffs to SQL.
- **executor.py**: ``ExecutorMixin`` — assembles and executes SQL commands.
- **migrator.py**: ``SqlMigrator`` — composes all mixins, orchestrates migration.

Usage
-----

All imports remain unchanged::

    from gnr.sql.gnrsqlmigration import SqlMigrator
"""

from .migrator import SqlMigrator
from .orm_extractor import OrmExtractor
from .db_extractor import DbExtractor
from gnr.sql.gnrsql_exceptions import GnrSqlException

from .structures import (
    ENTITY_TREE,
    COL_JSON_KEYS,
    GNR_DTYPE_CONVERTER,
    new_structure_root,
    new_schema_item,
    new_extension_item,
    new_event_trigger_item,
    new_table_item,
    new_column_item,
    new_constraint_item,
    new_relation_item,
    new_index_item,
    nested_defaultdict,
    camel_to_snake,
    json_equal,
    json_to_tree,
    clean_attributes,
    hashed_name,
)

__all__ = [
    'SqlMigrator',
    'OrmExtractor',
    'DbExtractor',
    'GnrSqlException',
    'ENTITY_TREE',
    'COL_JSON_KEYS',
    'GNR_DTYPE_CONVERTER',
    'new_structure_root',
    'new_schema_item',
    'new_extension_item',
    'new_event_trigger_item',
    'new_table_item',
    'new_column_item',
    'new_constraint_item',
    'new_relation_item',
    'new_index_item',
    'nested_defaultdict',
    'camel_to_snake',
    'json_equal',
    'json_to_tree',
    'clean_attributes',
    'hashed_name',
]
