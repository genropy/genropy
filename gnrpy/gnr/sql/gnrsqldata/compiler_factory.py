#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_compiler_factory : SQL query compiler selection
# Copyright (c) : 2004 - 2026 Softwell sas - Milano
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU.
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Selection of the SQL query compiler an instance runs on.

Two compiler classes exist: the frozen ``SqlQueryCompiler`` of
``compiler.py`` and ``SqlQueryCompilerNext`` of ``compiler_next.py``, the copy
that receives new work.  An instance opts in to the copy with the experimental
flag::

    <experimental>
        <db next_sql_compiler="True"/>
    </experimental>

in its configuration.  A false or missing flag, or a database with no
application attached (standalone mode), keeps the frozen compiler.

``queryCompilerClass`` is called at the two points where a compiler is built:
``SqlQuery.compileQuery`` and ``SqlRecord.compileQuery``.
"""

from gnr.sql.gnrsqldata.compiler import SqlQueryCompiler
from gnr.sql.gnrsqldata.compiler_next import SqlQueryCompilerNext


def queryCompilerClass(db):
    """Return the query compiler class configured for *db*.

    Args:
        db: A :class:`GnrSqlDb <gnr.sql.gnrsql.GnrSqlDb>` instance.

    Returns:
        type: ``SqlQueryCompilerNext`` when the experimental flag
        ``next_sql_compiler`` of the ``db`` group is on,
        ``SqlQueryCompiler`` otherwise.
    """
    if db.application and db.application.experimentalFlag('db', 'next_sql_compiler'):
        return SqlQueryCompilerNext
    return SqlQueryCompiler
