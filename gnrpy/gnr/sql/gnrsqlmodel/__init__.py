# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel : Package facade — re-exports all public names
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

"""GenroPy SQL model package.

This package was refactored from the monolithic ``gnrsqlmodel.py``
(~2 150 lines) into focused modules:

- :mod:`helpers` — standalone functions and exceptions
- :mod:`obj` — base model object (``DbModelObj``) and
  package (``DbPackageObj``)
- :mod:`columns` — column classes (``DbBaseColumnObj``,
  ``DbColumnObj``, ``DbVirtualColumnObj``, ``AliasColumnWrapper``)
- :mod:`containers` — list containers, alias, colgroup,
  subtable, and index objects
- :mod:`resolvers` — ``RelationTreeResolver`` and
  ``ModelSrcResolver``
- :mod:`table` — ``DbTableObj``
- :mod:`model` — ``DbModel`` and ``DbModelSrc``

All public names are re-exported here so that existing imports like
``from gnr.sql.gnrsqlmodel import DbModel`` continue to work.

The ``moduleDict('gnr.sql.gnrsqlmodel', 'sqlclass,sqlresolver')`` call
in ``DbModel.build()`` relies on all classes being importable from this
namespace — the star-imports below ensure that.
"""

from __future__ import annotations

# -- Helpers (standalone functions + exceptions) ---------------------------
from gnr.sql.gnrsqlmodel.helpers import (  # noqa: F401
    ConfigureAfterStartError,
    NotExistingTableError,
    bagItemFormula,
    toolFormula,
)

# -- Base model objects ----------------------------------------------------
from gnr.sql.gnrsqlmodel.obj import (  # noqa: F401
    DbModelObj,
    DbPackageObj,
)

# -- Column objects --------------------------------------------------------
from gnr.sql.gnrsqlmodel.columns import (  # noqa: F401
    AliasColumnWrapper,
    DbBaseColumnObj,
    DbColumnObj,
    DbVirtualColumnObj,
)

# -- Container and list objects --------------------------------------------
from gnr.sql.gnrsqlmodel.containers import (  # noqa: F401
    DbColAliasListObj,
    DbColgroupListObj,
    DbColgroupObj,
    DbColumnListObj,
    DbIndexListObj,
    DbIndexObj,
    DbPackageListObj,
    DbSubtableListObj,
    DbSubtableObj,
    DbTableAliasObj,
    DbTableListObj,
    DbTblAliasListObj,
)

# -- BagResolver subclasses -----------------------------------------------
from gnr.sql.gnrsqlmodel.resolvers import (  # noqa: F401
    ModelSrcResolver,
    RelationTreeResolver,
)

# -- Table object ----------------------------------------------------------
from gnr.sql.gnrsqlmodel.table import DbTableObj  # noqa: F401

# -- Model orchestration ---------------------------------------------------
from gnr.sql.gnrsqlmodel.model import (  # noqa: F401
    DbModel,
    DbModelSrc,
)

__all__ = [
    # helpers
    'bagItemFormula',
    'toolFormula',
    'NotExistingTableError',
    'ConfigureAfterStartError',
    # obj
    'DbModelObj',
    'DbPackageObj',
    # columns
    'DbBaseColumnObj',
    'DbColumnObj',
    'DbVirtualColumnObj',
    'AliasColumnWrapper',
    # containers
    'DbTableAliasObj',
    'DbColgroupObj',
    'DbSubtableObj',
    'DbTblAliasListObj',
    'DbColAliasListObj',
    'DbColumnListObj',
    'DbColgroupListObj',
    'DbSubtableListObj',
    'DbIndexListObj',
    'DbPackageListObj',
    'DbTableListObj',
    'DbIndexObj',
    # resolvers
    'RelationTreeResolver',
    'ModelSrcResolver',
    # table
    'DbTableObj',
    # model
    'DbModel',
    'DbModelSrc',
]


# -- moduleDict compatibility ----------------------------------------------
# ``moduleDict('gnr.sql.gnrsqlmodel', 'sqlclass,sqlresolver')`` filters
# classes by ``cls.__module__ == module.__name__``.  Since the classes
# now live in sub-modules their ``__module__`` no longer matches
# ``'gnr.sql.gnrsqlmodel'``.  We patch it here so that ``moduleDict``
# continues to find every class with a ``sqlclass`` attribute.
_PACKAGE_NAME = __name__  # 'gnr.sql.gnrsqlmodel'

for _cls in list(locals().values()):
    if isinstance(_cls, type) and hasattr(_cls, 'sqlclass'):
        _cls.__module__ = _PACKAGE_NAME
