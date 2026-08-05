# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqlmodel.resolvers : BagResolver subclasses for relation trees
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

"""BagResolver subclasses for lazy-loading relation trees and model sources.

``RelationTreeResolver`` builds the relation tree lazily for each table,
using thread-safe locking.  ``ModelSrcResolver`` provides a cached
resolver for the model source Bag.
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrbag import Bag, BagResolver
from gnr.sql import logger


class RelationTreeResolver(BagResolver):
    """Lazy-loading resolver for the relation tree of a table.

    Builds a :class:`Bag` tree of columns and relations on first access,
    with thread-safe double-checked locking.

    Class kwargs:
        main_tbl: The root table (``pkg.table``) that owns this tree.
        tbl_name: The table name being resolved.
        pkg_name: The package name.
        path: Breadcrumb path for cycle detection.
        parentpath: Parent column path for nested relations.
    """

    classKwargs = {
        'cacheTime': 0,
        'readOnly': True,
        'main_tbl': None,
        'tbl_name': None,
        'pkg_name': None,
        'path': None,
        'parentpath': None,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(RelationTreeResolver, self).__init__(*args, **kwargs)

    def resolverSerialize(self) -> Any:
        """Serialize this resolver for pickling.

        Replaces the ``dbroot`` reference with a serialization-safe
        ``_serialized_app_handler`` marker.
        """
        args = list(self._initArgs)
        kwargs = dict(self._initKwargs)
        kwargs['_serialized_app_handler'] = 'maindb'
        return BagResolver.resolverSerialize(self, args=args, kwargs=kwargs)

    def setDbroot(self, dbroot: Any) -> None:
        """Attach the database root reference.

        Args:
            dbroot: The ``GnrSqlDb`` instance.
        """
        self.dbroot = dbroot

    def load(self) -> Bag | None:
        """Load the relation tree.

        Returns:
            A :class:`Bag` tree of columns and relations, or ``None``
            if the target package is not loaded.
        """
        if self.dbroot.package(self.pkg_name) is None:
            logger.warning(
                "Relation to unloaded package '%s' skipped (table: %s)",
                self.pkg_name, self.tbl_name,
            )
            return None
        self.main_table_obj = self.dbroot.model.table(self.main_tbl)
        return self._fields(
            self.tbl_name, self.pkg_name, self.path, self.parentpath
        )

    def _fields(
        self,
        table: str,
        pkg_name: str,
        path: list[Any] | None = None,
        parentpath: list[Any] | None = None,
    ) -> Bag:
        """Build the relation tree for a table.

        Recursively resolves one-to-many and many-to-one relations,
        creating child ``RelationTreeResolver`` instances for each
        related table.

        Args:
            table: The table name.
            pkg_name: The package name.
            path: Breadcrumb path for visited tables/relations.
            parentpath: Parent column path for nested relations.

        Returns:
            A :class:`Bag` with columns and nested resolvers.
        """
        path = path or []
        parentpath = parentpath or []
        if parentpath:
            tbltuple = tuple(parentpath)
        else:
            tbltuple = ('%s_%s' % (pkg_name, table),)
        if path:
            prfx = []
            for p in path:
                if p == '*O':
                    pass
                elif p == '*M':
                    pass
                elif p == '*m':
                    pass
                else:
                    if p.startswith('%s_' % self.pkg_name):
                        p = p[len(self.pkg_name) + 1:]
                    prfx.append(p)
            prfx = '_'.join(prfx)
        else:
            prfx = None
        tableFullName = '%s_%s' % (pkg_name, table)
        result = Bag()
        result.tbl_name = table
        result.pkg_name = pkg_name

        cols = list(self.dbroot.package(pkg_name).table(table)['columns'].values())
        vcols = list(self.dbroot.package(pkg_name).table(table)['virtual_columns'].values())
        relations = self.dbroot.model.relations('%s.%s' % (pkg_name, table))
        onerels = {}
        manyrels = []
        if relations:
            onerels = {
                a['many_relation'].replace('.', '_'): (lbl, a)
                for lbl, a in relations.digest('#k,#a') if a['mode'] == 'O'
            }
            manyrels = [
                (lbl, a, a['many_relation'].replace('.', '_'))
                for lbl, a in relations.digest('#k,#a') if a['mode'] == 'M'
            ]
        for col in cols:
            fullname = '%s_%s_%s' % (pkg_name, table, col.name)
            result.setItem(col.name, None, col.attributes, prfx=prfx, table=table, pkg=pkg_name)
            lbl, relpars = onerels.get(fullname, (None, None))
            if lbl:
                un_sch, un_tbl = relpars['one_relation'].split('.')[:2]
                un_schtbl = '%s_%s' % (un_sch, un_tbl)
                child_kwargs = {
                    'main_tbl': self.main_tbl,
                    'tbl_name': un_tbl,
                    'pkg_name': un_sch,
                    'path': path + ['*O', un_schtbl],
                    'parentpath': parentpath + [col],
                    'cacheTime': self.cacheTime,
                }
                child = RelationTreeResolver(**child_kwargs)
                child.setDbroot(self.dbroot)
                result.setItem(lbl, child, col.attributes, joiner=relpars)
        for vcol in vcols:
            fullname = '%s_%s_%s' % (pkg_name, table, vcol.name)
            lbl, relpars = onerels.get(fullname, (None, None))
            if lbl:
                un_sch, un_tbl = relpars['one_relation'].split('.')[:2]
                un_schtbl = '%s_%s' % (un_sch, un_tbl)
                child_kwargs = {
                    'main_tbl': self.main_tbl,
                    'tbl_name': un_tbl,
                    'pkg_name': un_sch,
                    'path': path + ['*O', un_schtbl],
                    'parentpath': parentpath + [col],
                    'cacheTime': self.cacheTime,
                }
                child = RelationTreeResolver(**child_kwargs)
                child.setDbroot(self.dbroot)
                result.setItem(lbl, child, col.attributes, joiner=relpars)
        for label, relpars, relcol in manyrels:
            sch, tbl, col = relpars['many_relation'].split('.')
            schtbl = '%s_%s' % (sch, tbl)
            if (len(cols) == 1 and cols[0].name.endswith('_id')):
                relmode = '*M'
            else:
                relmode = '*m'
            child_kwargs = {
                'main_tbl': self.main_tbl,
                'tbl_name': tbl,
                'pkg_name': sch,
                'path': path + [relmode, schtbl],
                'parentpath': parentpath + [col],
                'cacheTime': self.cacheTime,
            }
            child = RelationTreeResolver(**child_kwargs)
            child.setDbroot(self.dbroot)
            result.setItem(label, child, joiner=relpars)
        return result


class ModelSrcResolver(BagResolver):
    """Cached resolver that returns the model source Bag.

    Used for serialization/deserialization of the model source tree.
    """

    classKwargs = {'cacheTime': 300, 'readOnly': False, 'dbroot': None}
    classArgs = ['dbId']

    def load(self) -> Any:
        """Return the model source Bag."""
        return self.dbroot.model.src

    def resolverSerialize(self) -> Any:
        """Serialize this resolver, stripping the ``dbroot`` reference."""
        args = list(self._initArgs)
        kwargs = dict(self._initKwargs)
        kwargs.pop('dbroot')
        return BagResolver.resolverSerialize(self, args=args, kwargs=kwargs)
