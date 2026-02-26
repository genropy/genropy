# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable : SQL table object — sub-package facade
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""GenroPy SQL Table — sub-package facade.

This package replaces the former monolithic ``gnrsqltable.py`` module.
All public names are re-exported here for backward compatibility::

    from gnr.sql.gnrsqltable import SqlTable
    from gnr.sql.gnrsqltable import GnrSqlSaveException
    from gnr.sql.gnrsqltable import EXCEPTIONS

Internal organisation:

- :mod:`~gnrsqltable.table` — :class:`SqlTable` (assembled from mixins)
- :mod:`~gnrsqltable.helpers` — decorators and :class:`RecordUpdater`
- :mod:`~gnrsqltable.columns` — column access, properties, variant columns
- :mod:`~gnrsqltable.query` — query building, WHERE translation
- :mod:`~gnrsqltable.record` — record building, caching, retrieval
- :mod:`~gnrsqltable.crud` — insert / update / delete operations
- :mod:`~gnrsqltable.triggers` — trigger hooks, protection, validation
- :mod:`~gnrsqltable.serialization` — JSON / XML serialization
- :mod:`~gnrsqltable.copy` — copy, paste, duplicate, archive
- :mod:`~gnrsqltable.utils` — pkey helpers, data export, totalizers, retention
"""

from __future__ import annotations

from gnr.sql.gnrsql_exceptions import GnrSqlException

__version__ = '1.0b'


# ---------------------------------------------------------------------------
#  Exceptions
# ---------------------------------------------------------------------------

class GnrSqlSaveException(GnrSqlException):
    """Raised when a record cannot be saved.

    * **code**: GNRSQL-003
    """
    code = 'GNRSQL-003'
    description = '!!Genro SQL Save Exception'
    caption = (
        "!!The record %(rowcaption)s in table %(tablename)s "
        "cannot be saved:%(msg)s"
    )


class GnrSqlDeleteException(GnrSqlException):
    """Raised when a record cannot be deleted.

    * **code**: GNRSQL-004
    """
    code = 'GNRSQL-004'
    description = '!!Genro SQL Delete Exception'
    caption = (
        "!!The record %(rowcaption)s in table %(tablename)s "
        "cannot be deleted:%(msg)s"
    )


class GnrSqlProtectUpdateException(GnrSqlException):
    """Raised when a record is protected from updates.

    * **code**: GNRSQL-011
    """
    code = 'GNRSQL-011'
    description = '!!Genro SQL Protect Update Exception'
    caption = (
        "!!The record %(rowcaption)s in table %(tablename)s "
        "is not updatable:%(msg)s"
    )


class GnrSqlProtectDeleteException(GnrSqlException):
    """Raised when a record is protected from deletion.

    * **code**: GNRSQL-012
    """
    code = 'GNRSQL-012'
    description = '!!Genro SQL Protect Delete Exception'
    caption = (
        "!!The record %(rowcaption)s in table %(tablename)s "
        "is not deletable:%(msg)s"
    )


class GnrSqlProtectValidateException(GnrSqlException):
    """Raised when a record fails validation.

    * **code**: GNRSQL-013
    """
    code = 'GNRSQL-013'
    description = '!!Genro SQL Protect Validate Exception'
    caption = (
        "!!The record %(rowcaption)s in table %(tablename)s "
        "contains invalid data:%(msg)s"
    )


class GnrSqlBusinessLogicException(GnrSqlException):
    """Raised when an operation violates business logic.

    * **code**: GNRSQL-021
    """
    code = 'GNRSQL-021'
    description = '!!Genro SQL Business Logic Exception'
    caption = (
        '!!The requested operation violates the internal '
        'business logic: %(msg)s'
    )


class GnrSqlStandardException(GnrSqlException):
    """Generic SQL exception with customisable description.

    * **code**: GNRSQL-023
    """
    code = 'GNRSQL-023'
    description = '!!%(description)s'
    caption = '!!%(msg)s'


class GnrSqlNotExistingColumnException(GnrSqlException):
    """Raised when referencing a non-existing column.

    * **code**: GNRSQL-081
    """
    code = 'GNRSQL-081'
    description = '!!Genro SQL Not Existing Column Exception'
    caption = (
        "!!Column %(column)s not existing in table %(tablename)s "
    )


# ---------------------------------------------------------------------------
#  Exception registry
# ---------------------------------------------------------------------------

EXCEPTIONS = {
    'save': GnrSqlSaveException,
    'delete': GnrSqlDeleteException,
    'protect_update': GnrSqlProtectUpdateException,
    'protect_delete': GnrSqlProtectDeleteException,
    'protect_validate': GnrSqlProtectValidateException,
    'business_logic': GnrSqlBusinessLogicException,
    'standard': GnrSqlStandardException,
    'not_existing_column': GnrSqlNotExistingColumnException,
}


# ---------------------------------------------------------------------------
#  Re-exports from sub-modules
# ---------------------------------------------------------------------------

from gnr.sql.gnrsqltable.table import SqlTable  # noqa: E402
from gnr.sql.gnrsqltable.helpers import (  # noqa: E402
    RecordUpdater,
    add_sql_comment,
    orm_audit_log,
)

__all__ = [
    # Main class
    'SqlTable',
    # Helpers
    'RecordUpdater',
    'add_sql_comment',
    'orm_audit_log',
    # Exceptions
    'GnrSqlSaveException',
    'GnrSqlDeleteException',
    'GnrSqlProtectUpdateException',
    'GnrSqlProtectDeleteException',
    'GnrSqlProtectValidateException',
    'GnrSqlBusinessLogicException',
    'GnrSqlStandardException',
    'GnrSqlNotExistingColumnException',
    'EXCEPTIONS',
    # Version
    '__version__',
]
