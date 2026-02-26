# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql : Genro SQL db connection (package facade)
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

"""Genro SQL database connection package.

Re-exports all public names for backward compatibility.
The actual implementations live in:

* ``gnrsql/helpers.py``      — decorators, exceptions, TempEnv, TriggerStack, DbLocalizer
* ``gnrsql/db.py``           — GnrSqlDb (assembles all mixins)
* ``gnrsql/connections.py``  — ConnectionMixin
* ``gnrsql/env.py``          — EnvMixin
* ``gnrsql/execute.py``      — ExecuteMixin
* ``gnrsql/write.py``        — WriteMixin
* ``gnrsql/transactions.py`` — TransactionMixin
* ``gnrsql/query.py``        — QueryMixin
* ``gnrsql/schema.py``       — SchemaMixin
* ``gnrsql/runtime_model.py`` — RuntimeModel
"""

# Core class
from gnr.sql.gnrsql.db import GnrSqlDb  # noqa: F401

# Helpers, decorators, exceptions
from gnr.sql.gnrsql.helpers import (  # noqa: F401
    MAIN_CONNECTION_NAME,
    DbLocalizer,
    GnrMissedCommitException,
    GnrSqlException,
    GnrSqlExecException,
    TempEnv,
    TriggerStack,
    TriggerStackItem,
    in_triggerstack,
    sql_audit,
)


# Runtime model
from gnr.sql.gnrsql.runtime_model import RuntimeModel  # noqa: F401
