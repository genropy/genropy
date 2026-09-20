# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.structure : Database schema introspection
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

"""Database schema introspection mixin.

Provides :class:`StructureMixin` — the tables tree and the relation
structure of the application database, exposed as RPC endpoints.

This module is the copy that receives new work.  The module of the same
name under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never
imported from here.

The methods with no caller anywhere in the tree are not part of the copy:
``getPackages``/``rpc_getPackages``, ``getTables``/``rpc_getTables``
and ``getTableFields``/``rpc_getTableFields``.
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrbag import Bag


class StructureMixin:
    """Mixin for database schema introspection.

    All methods rely on ``self.db`` (provided by the main handler class)
    to navigate the ORM model and return the structure of packages,
    tables and their relations.
    """

    def getTablesTree(self) -> Bag:
        """Build a hierarchical :class:`Bag` of all non-reserved packages and their tables.

        Returns:
            A :class:`Bag` whose first-level keys are package identifiers
            and whose second-level keys are table identifiers.
        """
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

    rpc_getTablesTree = getTablesTree

    def dbStructure(self, path: str = '', **kwargs: Any) -> Bag:
        """Return a recursive :class:`Bag` representing the database structure.

        When called without *path* the full package tree is returned.
        Sub-trees are represented as JavaScript remote-resolver strings
        so that the client can lazily expand them.

        Args:
            path: Dot-separated path into the database model
                (e.g. ``"pkg.tables.tbl.relations"``).

        Returns:
            A :class:`Bag` whose nodes are either leaf values or JS
            resolver expressions for further lazy expansion.
        """
        curr = self.db.packages
        if path:
            curr = curr[path]
            path = path + '.'
        return self._dbStructureInner(curr, path)

    rpc_dbStructure = dbStructure

    def _dbStructureInner(self, where: Any, path: str) -> Bag:
        """Recursively build the database structure :class:`Bag`.

        Args:
            where: The current node in the ORM model tree to expand.
            path: The accumulated dot-path used to generate JS resolver
                expressions.

        Returns:
            A :class:`Bag` with child nodes that are either leaf values
            or JS remote-resolver strings.

        Note:
            SMELL: The method uses ``!=`` to compare with ``None``
            (``elem.resolver != None``) instead of ``is not None``.
            This works but violates PEP 8 recommendations.

            SMELL: The JS resolver string is built via inline string
            formatting rather than through a dedicated helper, making
            it fragile to changes in the client-side API.
        """
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
                if elem.resolver != None:  # SMELL: should be ``is not None``
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
