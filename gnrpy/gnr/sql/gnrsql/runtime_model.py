# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.runtime_model : Temporary model extensions for queries
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

"""Runtime model extensions — temporary injection into queries.

Provides ``RuntimeModel``, a container/context manager that collects
virtual column and relation definitions and activates them inside a
``with`` block.

Basic formula column::

    rm = db.runtimeModel()
    customer = rm.table('invc.customer')
    customer.formulaColumn('n_invoices', dtype='L',
        select=dict(table='invc.invoice', columns='COUNT(*)',
                    where='$customer_id=#THIS.id'))

    with rm:
        result = db.query('invc.customer',
            columns='$account_name, $n_invoices').fetch()
    # outside: runtime model extensions are gone

Formula column with relation navigation::

    customer.formulaColumn('top_product_id', dtype='T',
        select=dict(table='invc.invoice_row',
                    columns='$product_id',
                    where='@invoice_id.customer_id=#THIS.id',
                    group_by='$product_id',
                    order_by='COUNT(*) DESC',
                    limit=1,
        )).relation('product.id')

    with rm:
        # navigate through the runtime relation
        result = db.query('invc.customer',
            columns='$account_name, @top_product_id.description').fetch()

Reusable across multiple with blocks::

    with rm:
        r1 = db.query(...).fetch()
    with rm:
        r2 = db.query(...).fetch()
"""

from __future__ import annotations

from typing import Any

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqlmodel.columns import DbVirtualColumnObj
from gnr.sql.gnrsqlmodel.resolvers import RelationTreeResolver


class _DbModelStub:
    """Minimal stub so DbModelSrc.virtual_column() skips auto_static.

    The ``db`` attribute exposes ``auto_static_enabled = False`` so
    that ``virtual_column()`` never enters the late-compilation block.
    """

    class db:
        auto_static_enabled = False

    obj = None


class RuntimeModel:
    """Container and context manager for temporary model extensions.

    Collects virtual column and relation definitions for one or more
    tables. Activates them via ``with rm:`` — extensions are visible
    only inside the ``with`` block.

    Attributes:
        db: The ``GnrSqlDb`` instance.
    """

    def __init__(self, db: Any) -> None:
        self.db = db
        self._columns: dict[str, dict[str, DbVirtualColumnObj]] = {}
        self._relations: Bag = Bag()
        self._relation_trees: dict[str, Bag | None] = {}
        self._temp_env = None

    def table(self, fullname: str) -> RuntimeTableProxy:
        """Return a proxy for adding runtime columns to a table.

        Args:
            fullname: Table full name (``pkg.table``).
        """
        return RuntimeTableProxy(self, fullname)

    def columns_for(self, fullname: str) -> dict[str, DbVirtualColumnObj]:
        """Return runtime columns for a table.

        Args:
            fullname: Table full name (``pkg.table``).

        Returns:
            Dict mapping lowercase column names to ``DbVirtualColumnObj``.
        """
        return self._columns.get(fullname, {})

    def relation_tree_for(self, pkg_name: str, tbl_name: str) -> Bag | None:
        """Return a Bag with runtime relation entries for a table.

        The Bag has ``tbl_name`` and ``pkg_name`` attributes for
        compatibility with the compiler's relation navigation.

        Args:
            pkg_name: Package name.
            tbl_name: Table name.

        Returns:
            A Bag with runtime relation entries, or ``None``.
        """
        cache_key = f'{pkg_name}.{tbl_name}'
        if cache_key in self._relation_trees:
            return self._relation_trees[cache_key]

        sub_bag = self._relations[f'{pkg_name}.{tbl_name}']
        if not sub_bag:
            self._relation_trees[cache_key] = None
            return None

        tree = Bag()
        tree.tbl_name = tbl_name
        tree.pkg_name = pkg_name
        main_tbl = f'{pkg_name}.{tbl_name}'
        for node in sub_bag:
            rel_attrs = dict(node.attr)
            child = self._makeRelationResolver(main_tbl, rel_attrs)
            if child:
                tree.setItem(node.label, child, joiner=rel_attrs)

        self._relation_trees[cache_key] = tree
        return tree

    def _makeRelationResolver(self, main_tbl: str, rel_attrs: dict) -> RelationTreeResolver | None:
        """Create a RelationTreeResolver for a runtime relation entry.

        Returns None if the mode is not recognized.
        """
        mode = rel_attrs.get('mode')
        if mode == 'O':
            rel_ref = rel_attrs['one_relation']
            path_prefix = '*O'
        elif mode == 'M':
            rel_ref = rel_attrs['many_relation']
            path_prefix = '*m'
        else:
            return None
        ref_pkg, ref_tbl = rel_ref.split('.')[:2]
        child = RelationTreeResolver(
            main_tbl=main_tbl,
            tbl_name=ref_tbl,
            pkg_name=ref_pkg,
            path=[path_prefix, f'{ref_pkg}_{ref_tbl}'],
            parentpath=[],
            cacheTime=-1,
        )
        child.setDbroot(self.db)
        return child

    def __enter__(self) -> Any:
        self._previous_runtime_model = self.db.currentRuntimeModel
        self.db.currentRuntimeModel = self
        return self.db

    def __exit__(self, *args: Any) -> None:
        self.db.currentRuntimeModel = self._previous_runtime_model
        self._previous_runtime_model = None


class RuntimeTableProxy:
    """Proxy for adding runtime columns to a specific table.

    Uses ``DbModelSrc`` to build source nodes with the standard API,
    then compiles them into ``DbVirtualColumnObj`` instances without
    touching the static model.

    Created by ``rm.table('pkg.table')``.
    """

    def __init__(self, rm: RuntimeModel, fullname: str) -> None:
        self._rm = rm
        self._fullname = fullname
        pkg, tbl = fullname.split('.')
        self._pkg = pkg
        self._tbl = tbl
        self._src = self._make_table_src()

    def _make_table_src(self) -> Any:
        """Create a standalone DbModelSrc table node for runtime columns."""
        from gnr.sql.gnrsqlmodel.model import DbModelSrc

        src = DbModelSrc.makeRoot()
        src._dbmodel = _DbModelStub()
        tbl_src = src.child('package', 'packages.%s' % self._pkg)
        tbl_src = tbl_src.child('table_list', 'tables')
        tbl_src = tbl_src.child('table', self._tbl,
                                fullname=self._fullname,
                                pkg=self._pkg)
        return tbl_src

    def _compile_column(self, name: str) -> _RuntimeColumnChain:
        """Compile a source node into a DbVirtualColumnObj.

        Takes the virtual_column node just created by the source API
        and compiles it into a live DbVirtualColumnObj, stored in the
        RuntimeModel container.

        Args:
            name: Column name.

        Returns:
            A ``_RuntimeColumnChain`` for optional ``.relation()`` chaining.
        """
        vc_src_node = self._src['virtual_columns'].getNode(name)
        tbl_obj = self._rm.db.model.table(self._tbl, pkg=self._pkg)
        parent_container = tbl_obj['virtual_columns']

        col_obj = DbVirtualColumnObj(structnode=vc_src_node,
                                     parent=parent_container)
        parent_container.children.pop(name.lower(), None)

        self._rm._columns.setdefault(self._fullname, {})[name.lower()] = col_obj

        return _RuntimeColumnChain(self._rm, col_obj, self._pkg, self._tbl, name)

    def formulaColumn(
        self,
        name: str,
        sql_formula: str | None = None,
        select: Any = None,
        exists: Any = None,
        dtype: str = 'A',
        **kwargs: Any,
    ) -> _RuntimeColumnChain:
        """Add a runtime formula column.

        Uses the standard ``DbModelSrc.formulaColumn()`` API to build
        the source node, then compiles it.

        Args:
            name: Column name.
            sql_formula: SQL expression.
            select: Sub-select definition.
            exists: EXISTS sub-query definition.
            dtype: Data type (default ``'A'``).

        Returns:
            A ``_RuntimeColumnChain`` for optional ``.relation()`` chaining.
        """
        self._src.formulaColumn(name, sql_formula=sql_formula,
                                select=select, exists=exists,
                                dtype=dtype, **kwargs)
        return self._compile_column(name)

    def aliasColumn(
        self,
        name: str,
        relation_path: str,
        **kwargs: Any,
    ) -> _RuntimeColumnChain:
        """Add a runtime alias column.

        Args:
            name: Column name.
            relation_path: Dotted relation path.

        Returns:
            A ``_RuntimeColumnChain`` for optional ``.relation()`` chaining.
        """
        self._src.aliasColumn(name, relation_path=relation_path, **kwargs)
        return self._compile_column(name)

    def joinColumn(
        self,
        name: str,
        **kwargs: Any,
    ) -> _RuntimeColumnChain:
        """Add a runtime join column.

        Args:
            name: Column name.

        Returns:
            A ``_RuntimeColumnChain`` for optional ``.relation()`` chaining.
        """
        self._src.virtual_column(name, join_column=True, **kwargs)
        return self._compile_column(name)


class _RuntimeColumnChain:
    """Fluent chain returned by column methods for ``.relation()`` support."""

    def __init__(
        self,
        rm: RuntimeModel,
        col_obj: DbVirtualColumnObj,
        pkg: str,
        tbl: str,
        col_name: str,
    ) -> None:
        self._rm = rm
        self._col_obj = col_obj
        self._pkg = pkg
        self._tbl = tbl
        self._col_name = col_name

    def relation(
        self,
        related_column: str,
        relation_name: str | None = None,
        one_name: str | None = None,
        many_name: str | None = None,
        **kwargs: Any,
    ) -> _RuntimeColumnChain:
        """Register a runtime relation for this column.

        Adds the relation to the source node (so the compiler sees
        ``fldalias.virtual``) and registers O-mode and M-mode entries
        in the RuntimeModel relations Bag.

        Args:
            related_column: Target column (``pkg.table.column``
                or ``table.column``).
            relation_name: Override for the inverse-relation label.
            one_name: Display name for the one-to-many side.
            many_name: Display name for the many-to-one side.

        Returns:
            ``self`` for further chaining.
        """
        parts = related_column.split('.')
        if len(parts) == 2:
            rel_pkg = self._pkg
            rel_tbl, rel_col = parts
        else:
            rel_pkg, rel_tbl, rel_col = parts
        one_relation = f'{rel_pkg}.{rel_tbl}.{rel_col}'
        many_relation = f'{self._pkg}.{self._tbl}.{self._col_name}'

        # Add relation child to source node via standard API
        vc_src_node = self._col_obj.structnode.getValue()
        if vc_src_node is None:
            from gnr.sql.gnrsqlmodel.model import DbModelSrc
            vc_src_node = DbModelSrc()
            self._col_obj.structnode.setValue(vc_src_node)
        vc_src_node.setItem('relation', vc_src_node.__class__(),
                            related_column=one_relation)

        self._col_obj.attributes['virtual'] = True

        if relation_name is None:
            relation_name = f'{self._tbl}_{self._col_name}'

        # O-mode entry: pkg.table.@column_name
        o_key = f'{self._pkg}.{self._tbl}.@{self._col_name}'
        self._rm._relations.setItem(
            o_key, None,
            mode='O',
            many_relation=many_relation,
            one_relation=one_relation,
            one_rel_name=one_name,
            many_rel_name=many_name,
            relation_name=relation_name,
            virtual=True,
            foreignkey=False,
            case_insensitive=False,
            private_relation=True,
            **kwargs,
        )

        # M-mode entry: rel_pkg.rel_table.@relation_name
        m_key = f'{rel_pkg}.{rel_tbl}.@{relation_name}'
        self._rm._relations.setItem(
            m_key, None,
            mode='M',
            many_relation=many_relation,
            one_relation=one_relation,
            one_rel_name=one_name,
            many_rel_name=many_name,
            relation_name=relation_name,
            virtual=True,
            private_relation=True,
            **kwargs,
        )

        self._rm._relation_trees.clear()

        return self



# _VirtualColumnsWithRuntime lives in gnr.sql.gnrsqlmodel.table
# to avoid circular imports (runtime_model → gnrsqlmodel → table → runtime_model).
