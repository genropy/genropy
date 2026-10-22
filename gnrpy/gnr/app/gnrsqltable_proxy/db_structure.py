# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy.db_structure : database level part of the structure flows
# Copyright (c)     : 2004 - 2026 Softwell sas - Milano
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

"""Database level part of the getTablesTree and dbStructure flows.

:class:`DbStructureProxy` is attached to the database of a ``GnrApp`` by
``gnr.app.gnrapp.GnrSqlAppDb.structureProxy``.  Unlike its four siblings of
this package it belongs to the whole database and not to one table: the
flows it serves walk ``db.packages`` and the model, and never a single table.

It never references a web page.
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrbag import Bag


class DbStructureProxy:
    """Structure proxy of a database."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def composeTablesTree(self) -> Bag:
        """Build the two level Bag package -> tables of the non reserved packages; returns that Bag."""
        result = Bag()
        for pkg, pkgobj in list(self.db.packages.items()):
            if pkgobj.attributes.get('reserved', 'n').upper() != 'Y':
                tblbag = Bag()
                label = pkgobj.name_full.capitalize()
                result.setItem(pkg, tblbag, label=label)
                for tbl, tblobj in list(pkgobj.tables.items()):
                    label = tblobj.name_full.capitalize()
                    tblbag.setItem(tbl, None, label=label, tableid='%s.%s' % (pkg, tbl))
        return result

    def composeStructure(self, path: str = '') -> Bag:
        """Build the model structure Bag under *path*, sub-trees as JS remote resolvers; returns that Bag."""
        curr = self.db.packages
        if path:
            curr = curr[path]
            path = path + '.'
        return self._composeStructureInner(curr, path)

    def _composeStructureInner(self, where: Any, path: str) -> Bag:
        result = Bag()
        for elem in where:
            if hasattr(elem, 'resolver'):
                attributes = {}
                attributes.update(elem.getAttr())
                if 'joiner' in attributes:
                    joiner = attributes.pop('joiner')
                    attributes.update(joiner or {})
                label = elem.label
                attributes['caption'] = attributes.get('name_long')
                if elem.resolver != None:  # noqa: E711
                    result.setItem(label, "genro.rpc.remoteResolver('app.dbStructure',{path:'%s'})" % (path + label),
                                   attributes, _T='JS')
                else:
                    value = elem.value
                    if hasattr(value, '__len__'):
                        if len(value):
                            result.setItem(label,
                                           "genro.rpc.remoteResolver('app.dbStructure',{path:'%s'})" % (path + label),
                                           attributes, _T='JS')
                        else:
                            result.setItem(label, None)
                    else:
                        result.setItem(label, elem.value, attributes)
            elif hasattr(where, '__getitem__'):
                if isinstance(where, Bag):
                    n = where.getNode(elem)
                    value = n.value
                    attributes = n.getAttr()
                else:
                    value = where[elem]
                    attributes = getattr(value, 'attributes', {})
                label = elem
                attributes['caption'] = attributes.get('name_long')
                if len(value):
                    result.setItem(label, "genro.rpc.remoteResolver('app.dbStructure',{path:'%s'})" % (path + label),
                                   attributes, _T='JS')
                else:
                    result.setItem(label, None, attributes)
            else:
                result.setItem(elem, None)
        return result
