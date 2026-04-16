# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsql.data_api_adapter : DataApiBackend adapter for GnrSqlDb
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

"""GnrSqlDb adapter for genro-data-api DataApiBackend protocol.

Bridges :class:`~gnr.sql.gnrsql.db.GnrSqlDb` to the
``DataApiBackend`` protocol defined in ``genro_data_api.core.backend``.

Maps GenroPy tables, columns, and query machinery to the four-method
protocol (``entity_sets``, ``entity_metadata``, ``query``, ``get_entity``).
FilterNode trees produced by the OData filter parser are translated to
GenroPy WHERE strings with named SQL parameters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_data_api.core.backend import QueryOptions, QueryResult
from genro_data_api.odata.filter_parser import (
    ComparisonNode,
    FilterNode,
    FunctionNode,
    LogicalNode,
    ODataFilterParser,
)

if TYPE_CHECKING:
    from gnr.sql.gnrsql.db import GnrSqlDb

# ---------------------------------------------------------------------------
# dtype → OData EDM type mapping
# ---------------------------------------------------------------------------

_DTYPE_TO_EDM: dict[str, str] = {
    'A': 'Edm.String',
    'C': 'Edm.String',
    'T': 'Edm.String',
    'X': 'Edm.String',
    'P': 'Edm.String',
    'I': 'Edm.Int32',
    'L': 'Edm.Int64',
    'R': 'Edm.Double',
    'N': 'Edm.Decimal',
    'B': 'Edm.Boolean',
    'D': 'Edm.Date',
    'H': 'Edm.TimeOfDay',
    'DH': 'Edm.DateTimeOffset',
}

# ---------------------------------------------------------------------------
# OData comparison operator → SQL operator
# ---------------------------------------------------------------------------

_ODATA_OP_TO_SQL: dict[str, str] = {
    'eq': '=',
    'ne': '!=',
    'gt': '>',
    'ge': '>=',
    'lt': '<',
    'le': '<=',
}


class GnrSqlDataApiAdapter:
    """DataApiBackend adapter wrapping a :class:`GnrSqlDb` instance.

    Implements the four-method read-only protocol required by genro-data-api.
    Accepts any ``GnrSqlDb`` instance and exposes all its loaded packages
    and tables as OData-compatible entity sets.
    """

    def __init__(self, db: GnrSqlDb) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # DataApiBackend protocol — entity_sets
    # ------------------------------------------------------------------

    def entity_sets(self) -> list[dict[str, Any]]:
        """List all tables across all packages as entity sets."""
        result = []
        for pkg_name, pkg_obj in self.db.packages.items():
            for tbl_name, tbl_model in pkg_obj.tables.items():
                entity_name = f'{pkg_name}.{tbl_name}'
                result.append({
                    'name': entity_name,
                    'title': tbl_model.attributes.get('name_long') or tbl_name,
                    'description': tbl_model.attributes.get('description') or '',
                })
        return result

    # ------------------------------------------------------------------
    # DataApiBackend protocol — entity_metadata
    # ------------------------------------------------------------------

    def entity_metadata(self, entity_name: str) -> dict[str, Any]:
        """Describe the structure of a single entity set."""
        table = self.db.table(entity_name)
        model = table.model

        pkeys: list[str] = list(model.pkeys) if model.pkeys else [model.pkey]

        properties: list[dict[str, Any]] = []

        for col_name, col_obj in model.columns.items():
            prop: dict[str, Any] = {
                'name': col_name,
                'type': _DTYPE_TO_EDM.get(col_obj.dtype or 'A', 'Edm.String'),
                'nullable': not col_obj.attributes.get('required'),
                'computed': False,
            }
            size = col_obj.attributes.get('size')
            if size:
                prop['maxLength'] = size
            properties.append(prop)

        for col_name, vc_obj in model.virtual_columns.items():
            if col_name.startswith('__'):
                continue
            properties.append({
                'name': col_name,
                'type': _DTYPE_TO_EDM.get(vc_obj.dtype or 'A', 'Edm.String'),
                'nullable': True,
                'computed': True,
            })

        navigation: list[dict[str, Any]] = []
        for rel_name, _rel_value, rel_attrs in model.relations_one.digest('#k,#v,#a'):
            joiner = rel_attrs.get('joiner') if rel_attrs else None
            if joiner:
                one_relation = joiner.get('one_relation', '')
                target = '.'.join(one_relation.split('.')[:2]) if one_relation else ''
                navigation.append({
                    'name': rel_name,
                    'target': target,
                    'collection': False,
                })

        return {
            'name': entity_name,
            'key': pkeys,
            'properties': properties,
            'navigation': navigation,
        }

    # ------------------------------------------------------------------
    # DataApiBackend protocol — query
    # ------------------------------------------------------------------

    def query(self, entity_name: str, options: QueryOptions) -> QueryResult:
        """Query an entity set using GenroPy query machinery."""
        table = self.db.table(entity_name)

        columns: str | None = (
            ','.join(f'${c}' for c in options.select)
            if options.select
            else None
        )

        where: str | None = None
        where_params: dict[str, Any] = {}
        if options.filter_expr:
            parser = ODataFilterParser()
            tree = parser.parse(options.filter_expr)
            counter = [0]
            where, where_params = self._filter_node_to_gnr(tree, counter)

        order_by: str | None = None
        if options.order_by:
            order_by = ','.join(f'${col} {direction}' for col, direction in options.order_by)

        q = table.query(
            columns=columns,
            where=where,
            order_by=order_by,
            limit=options.top,
            offset=options.skip,
            **where_params,
        )
        raw_records = q.fetch()
        records = [dict(row) for row in raw_records]

        total_count: int | None = None
        if options.count:
            count_q = table.query(
                columns=f'${table.pkey}',
                where=where,
                **where_params,
            )
            total_count = count_q.count()

        return QueryResult(records=records, total_count=total_count)

    # ------------------------------------------------------------------
    # DataApiBackend protocol — get_entity
    # ------------------------------------------------------------------

    def get_entity(self, entity_name: str, key: Any) -> dict[str, Any] | None:
        """Fetch a single entity by primary key."""
        table = self.db.table(entity_name)
        record = table.record(pkey=key, ignoreMissing=True, mode='dict')
        if not record:
            return None
        return dict(record)

    # ------------------------------------------------------------------
    # Internal — FilterNode → GenroPy WHERE translation
    # ------------------------------------------------------------------

    def _filter_node_to_gnr(
        self,
        node: FilterNode,
        counter: list[int],
    ) -> tuple[str, dict[str, Any]]:
        """Translate a FilterNode tree into a GenroPy WHERE clause.

        Args:
            node: Root of the FilterNode tree.
            counter: Single-element list used as a mutable integer
                     to generate unique parameter names.

        Returns:
            A (where_string, sqlparams) pair.
        """
        if isinstance(node, ComparisonNode):
            return self._translate_comparison(node, counter)
        if isinstance(node, FunctionNode):
            return self._translate_function(node, counter)
        if isinstance(node, LogicalNode):
            return self._translate_logical(node, counter)
        raise ValueError(f'Unknown FilterNode type: {type(node)}')

    def _translate_comparison(
        self,
        node: ComparisonNode,
        counter: list[int],
    ) -> tuple[str, dict[str, Any]]:
        sql_op = _ODATA_OP_TO_SQL.get(node.op)
        if sql_op is None:
            raise ValueError(f'Unsupported comparison operator: {node.op!r}')
        if node.value is None:
            clause = f'${node.field} IS NULL' if node.op == 'eq' else f'${node.field} IS NOT NULL'
            return clause, {}
        param_name = self._next_param(counter)
        clause = f'${node.field} {sql_op} :{param_name}'
        return clause, {param_name: node.value}

    def _translate_function(
        self,
        node: FunctionNode,
        counter: list[int],
    ) -> tuple[str, dict[str, Any]]:
        param_name = self._next_param(counter)
        if node.name == 'contains':
            pattern = f'%{node.value}%'
        elif node.name == 'startswith':
            pattern = f'{node.value}%'
        elif node.name == 'endswith':
            pattern = f'%{node.value}'
        else:
            raise ValueError(f'Unsupported filter function: {node.name!r}')
        clause = f'${node.field} ILIKE :{param_name}'
        return clause, {param_name: pattern}

    def _translate_logical(
        self,
        node: LogicalNode,
        counter: list[int],
    ) -> tuple[str, dict[str, Any]]:
        if node.op == 'not':
            child_clause, child_params = self._filter_node_to_gnr(node.children[0], counter)
            return f'NOT ({child_clause})', child_params
        sql_joiner = ' AND ' if node.op == 'and' else ' OR '
        parts: list[str] = []
        merged_params: dict[str, Any] = {}
        for child in node.children:
            child_clause, child_params = self._filter_node_to_gnr(child, counter)
            parts.append(f'({child_clause})')
            merged_params.update(child_params)
        return sql_joiner.join(parts), merged_params

    def _next_param(self, counter: list[int]) -> str:
        counter[0] += 1
        return f'_p{counter[0]}'


if __name__ == '__main__':
    # Quick smoke-test when run directly (requires a configured GnrSqlDb).
    import sys
    print('GnrSqlDataApiAdapter module loaded successfully.')
    sys.exit(0)
