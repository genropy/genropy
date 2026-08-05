"""Type-checking-only base classes for mixin modules.

At runtime ``TYPE_CHECKING`` is always ``False``, so every ``*BaseMixin``
name resolves to plain ``object`` — no import cycles, no runtime cost.

Type checkers (Pyright, mypy) treat ``TYPE_CHECKING`` as ``True`` and
therefore see the real assembled class, giving full attribute resolution,
autocomplete and error checking inside each mixin file.

Usage in a mixin module::

    from gnr.sql._typing import GnrSqlDbBaseMixin

    class ExecuteMixin(GnrSqlDbBaseMixin):
        def execute(self, sql):
            self.adapter.execute(sql)   # Pyright resolves this
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gnr.sql.gnrsql.db import GnrSqlDb as GnrSqlDbBaseMixin
    from gnr.sql.gnrsqltable.table import SqlTable as SqlTableBaseMixin
    from gnr.sql.gnrsqlmigration.migrator import SqlMigrator as SqlMigratorBaseMixin
else:
    GnrSqlDbBaseMixin = object
    SqlTableBaseMixin = object
    SqlMigratorBaseMixin = object

__all__ = ['GnrSqlDbBaseMixin', 'SqlTableBaseMixin', 'SqlMigratorBaseMixin']
