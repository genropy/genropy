# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrxls : XLS/XLSX writer wrappers
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
XLS/XLSX reader and writer classes — now implemented in gnr.core.flatfiles.
Importing from this module is deprecated; use gnr.core.flatfiles directly.
"""

import warnings

_MOVED_TO_FLATFILES = frozenset({'BaseXls', 'XlsWriter', 'XlsxWriter', 'XlsReader'})


def __getattr__(name):
    if name in _MOVED_TO_FLATFILES:
        warnings.warn(
            f"'{name}' has been moved to gnr.core.flatfiles. "
            f"Import from gnr.core.gnrxls is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        from gnr.core import flatfiles
        return getattr(flatfiles, name)
    raise AttributeError(f"module 'gnr.core.gnrxls' has no attribute {name!r}")
