#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata : Genro SQL query and data (package facade)
# Copyright (c) : 2004 - 2026 Softwell srl - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
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

# Re-export all public classes for backward compatibility.
# The actual implementations live in:
#   gnrsqldata/compiler.py  - SqlCompiledQuery, SqlQueryCompiler
#   gnrsqldata/query.py     - SqlQuery, SqlDataResolver
#   gnrsqldata/selection.py - SqlSelection
#   gnrsqldata/record.py    - SqlRecord, SqlRecordBag, SqlRelatedRecordResolver, SqlRelatedSelectionResolver

from gnr.sql.gnrsqldata.compiler import SqlCompiledQuery, SqlQueryCompiler  # noqa: F401
from gnr.sql.gnrsqldata.query import SqlQuery, SqlDataResolver  # noqa: F401
from gnr.sql.gnrsqldata.selection import SqlSelection  # noqa: F401
from gnr.sql.gnrsqldata.record import (SqlRecord, SqlRecordBag,  # noqa: F401
                                        SqlRelatedRecordResolver,
                                        SqlRelatedSelectionResolver)
