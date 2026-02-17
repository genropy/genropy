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

* ``gnrsql/gnrsql_helpers.py``      — decorators, exceptions, TempEnv, TriggerStack, DbLocalizer
* ``gnrsql/gnrsql_db.py``           — GnrSqlDb (assembles all mixins)
* ``gnrsql/gnrsql_connections.py``  — ConnectionMixin
* ``gnrsql/gnrsql_env.py``          — EnvMixin
* ``gnrsql/gnrsql_execute.py``      — ExecuteMixin
* ``gnrsql/gnrsql_write.py``        — WriteMixin
* ``gnrsql/gnrsql_transactions.py`` — TransactionMixin
* ``gnrsql/gnrsql_query.py``        — QueryMixin
* ``gnrsql/gnrsql_schema.py``       — SchemaMixin
"""

# Core class
from gnr.sql.gnrsql.gnrsql_db import GnrSqlDb  # noqa: F401

# Helpers, decorators, exceptions
from gnr.sql.gnrsql.gnrsql_helpers import (  # noqa: F401
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
