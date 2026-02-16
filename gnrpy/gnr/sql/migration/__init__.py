"""
migration - Genropy SQL migration package
============================================

This package contains the SQL migration system split into thematic
modules. It is a documented and organized version of ``gnrsqlmigration.py``.

Modules
--------

- **structures.py**: Constants, factory functions and shared utilities.
  Defines the normalized JSON format used by all components.

- **orm_extractor.py**: ``OrmExtractor`` class that reads the Genropy
  ORM model and produces a normalized JSON structure.

- **db_extractor.py**: ``DbExtractor`` class that queries the actual
  database (PostgreSQL) and produces a JSON structure in the same format.

- **diff_engine.py**: ``DiffMixin`` mixin that compares the two JSON
  structures using ``dictdiffer`` and produces typed events (added,
  changed, removed).

- **command_builder.py**: ``CommandBuilderMixin`` mixin with handlers
  to translate events into SQL commands (CREATE TABLE, ALTER COLUMN, etc.).

- **executor.py**: ``ExecutorMixin`` mixin for assembling SQL commands
  in the correct order and executing them on the database.

- **migrator.py**: ``SqlMigrator`` class that composes all mixins
  and orchestrates the complete migration flow.

Usage
------

::

    from gnr.sql.migration import SqlMigrator

    migrator = SqlMigrator(app.db)
    sql = migrator.getChanges()    # view changes
    migrator.applyChanges()        # apply changes
"""

from .migrator import SqlMigrator
from .orm_extractor import OrmExtractor
from .db_extractor import DbExtractor

__all__ = ['SqlMigrator', 'OrmExtractor', 'DbExtractor']
