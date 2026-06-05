# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.serialization : JSON/XML record serialization
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

"""JSON and XML record serialization.

Provides :class:`SerializationMixin` — a mixin for
:class:`~gnrsqltable.table.SqlTable` that handles conversion of records
to/from JSON and XML formats, including hierarchical cluster import/export.
"""

from __future__ import annotations

from collections import deque

from gnr.core import gnrstring
from gnr.core.gnrlang import MinValue, uniquify
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import deprecated
from gnr.sql._typing import SqlTableBaseMixin


class SerializationMixin(SqlTableBaseMixin):
    """JSON and XML record serialization."""

    # ------------------------------------------------------------------
    #  JSON cluster import
    # ------------------------------------------------------------------

    def insertRecordClusterFromJson(self, jsonCluster,
                                    dependencies=None,
                                    blacklist=None,
                                    record_extra=None,
                                    fkey_map=None):
        """Insert a hierarchical record cluster from JSON (breadth-first).

        :param jsonCluster: dict or JSON string
        :param dependencies: ``{table: [pkeys]}`` to validate before insert
        :param blacklist: tables/packages to exclude
        :param record_extra: dict of extra values to set
        :param fkey_map: dict mapping old pkeys to new ones
        :returns: the inserted root record
        """
        def is_blacklisted(table_name: str) -> bool:
            pkg = table_name.split('.', 1)[0]
            return table_name in blacklist or pkg in blacklist

        if dependencies:
            for table, pkeys in dependencies.items():
                if is_blacklisted(table):
                    continue
                tblobj = self.db.table(table)
                existing_records = tblobj.query(
                    where=f'${tblobj.pkey} IN :pkeys',
                    pkeys=pkeys,
                    columns=f"${tblobj.pkey}",
                    addPkeyColumn=False,
                    subtable='*',
                    ignorePartition=True,
                    excludeDraft=False,
                    excludeLogicalDeleted=False,
                ).fetch()
                existing_pkeys = {r[tblobj.pkey] for r in existing_records}
                missing_dependencies = set(pkeys) - existing_pkeys
                if missing_dependencies:
                    raise self.exception(
                        'business_logic',
                        msg=(
                            f'Missing dependencies: {missing_dependencies} '
                            f'in table {table}'
                        ),
                    )

        if isinstance(jsonCluster, str):
            jsonCluster = gnrstring.fromTypedJSON(jsonCluster)
        if not isinstance(jsonCluster, dict):
            raise ValueError("jsonCluster must be a dict or JSON string")

        fkey_map = fkey_map or {}
        record_extra = record_extra or {}
        for extra_field, extra_value in record_extra.items():
            relatedtable = self.column(extra_field).relatedTable()
            if jsonCluster.get(extra_field) and relatedtable is not None:
                table_map = fkey_map.setdefault(relatedtable.fullname, {})
                table_map[jsonCluster[extra_field]] = extra_value

        queue = deque()
        queue.append((self, jsonCluster, record_extra, True))
        root_record = None

        while queue:
            table_obj, cluster_data, extra, is_first_level = queue.popleft()
            record_data = {}
            for colname, colobj in table_obj.columns.items():
                value = cluster_data.pop(colobj.name, None)
                relatedtable = colobj.relatedTable()
                if relatedtable is not None:
                    reltbl = relatedtable.fullname
                    table_map = fkey_map.setdefault(reltbl, {})
                    if value in table_map:
                        value = table_map[value]
                    elif isinstance(value, str) and ':' in value:
                        value = relatedtable.dbtable.guessPkey(value)
                    elif is_blacklisted(reltbl):
                        value = None
                elif colobj.dtype == 'X' and value:
                    bagvalue = Bag()
                    bagvalue.fromJson(value)
                    value = bagvalue
                record_data[colname] = value

            old_pkey = record_data[table_obj.pkey]
            record = table_obj.newrecord(_fromRecord=record_data)
            record.update(extra)

            table_obj._doFieldTriggers('onInserting', record)
            table_obj.trigger_assignCounters(record=record)

            record[table_obj.pkey] = (
                record[table_obj.pkey] or table_obj.newPkeyValue(record)
            )
            table_obj.raw_insert(record)

            if is_first_level:
                root_record = record

            fkey_map.setdefault(table_obj.fullname, {})[old_pkey] = (
                record[table_obj.pkey]
            )
            record_pkey = record[table_obj.pkey]

            many_relations = {
                k: j for k, j in table_obj.relations.digest('#k,#a.joiner')
                if j and j.get('mode') == 'M' and not j.get('virtual')
            }

            for relation_key, joiner in many_relations.items():
                related_json_clusters = cluster_data.pop(relation_key, None)
                if not related_json_clusters:
                    continue
                related_table, fkey = joiner['many_relation'].rsplit('.', 1)
                for jc in related_json_clusters:
                    if not jc:
                        continue
                    queue.append((
                        table_obj.db.table(related_table),
                        jc,
                        {fkey: record_pkey},
                        False,
                    ))

        return root_record

    # ------------------------------------------------------------------
    #  JSON export
    # ------------------------------------------------------------------

    def recordToJson(self, record, related_many='cascade',
                     dependencies=None, blacklist=None,
                     nested=False, relation_conditions=None,
                     exported_keys=None, use_external_pkey=False):
        """Convert a record to JSON with optional related data.

        :param record: dict or primary key value
        :param related_many: ``'cascade'`` or ``None``
        :param dependencies: dict to collect FK dependencies
        :param blacklist: tables/packages to exclude
        :param nested: if ``True``, return nested dict without type conversion
        :param use_external_pkey: use external pkey column for FK values
        :returns: record as typed JSON or nested dict
        """
        if not hasattr(record, 'items'):
            record = dict(self.readColumns(
                pkey=record, columns=self.real_columns,
            ))

        main_pkey = record[self.pkey]
        dependencies = dependencies or {}
        relation_conditions = relation_conditions or {}
        exported_keys = exported_keys or set()

        exporting_key = f'{self.fullname}:{main_pkey}'
        exported_keys.add(exporting_key)

        for column in self.columns.values():
            relatedtable = column.relatedTable()
            value = record[column.name]
            if relatedtable is not None:
                external_pkey = relatedtable.attributes.get('external_pkey')
                if external_pkey and use_external_pkey:
                    record[column.name] = (
                        f'{external_pkey}:'
                        f'{relatedtable.dbtable.cachedRecord(value)[external_pkey]}'
                    )
                else:
                    dependencies.setdefault(relatedtable, []).append(value)
            elif column.dtype == 'X' and value:
                record[column.name] = Bag(value).toJson(nested=True)

        if isinstance(blacklist, str):
            blacklist = set(blacklist.split(','))
        elif isinstance(blacklist, list):
            blacklist = set(blacklist)
        else:
            blacklist = blacklist or set()

        def is_blacklisted(table_name: str) -> bool:
            pkg = table_name.split('.', 1)[0]
            return table_name in blacklist or pkg in blacklist

        if related_many:
            many_relations = {
                rel_key: joiner
                for rel_key, joiner in self.relations.digest('#k,#a.joiner')
                if joiner and joiner.get('mode') == 'M'
                and not joiner.get('virtual')
            }
            for rel_key, joiner in many_relations.items():
                if related_many == 'cascade' and not (
                    joiner.get('onDelete') == 'cascade'
                    or joiner.get('onDelete_sql') == 'cascade'
                ):
                    continue
                rel_condition_kwargs = relation_conditions.get(
                    joiner['many_relation'], {},
                )
                child_table, child_fkey = (
                    joiner['many_relation'].rsplit('.', 1)
                )
                if is_blacklisted(child_table):
                    continue
                related_records = self.db.table(
                    child_table,
                ).relatedSelectionToJson(
                    field=child_fkey,
                    value=main_pkey,
                    related_many=related_many,
                    dependencies=dependencies,
                    blacklist=blacklist,
                    condition=rel_condition_kwargs.get('condition', None),
                    condition_kwargs=rel_condition_kwargs,
                    relation_conditions=relation_conditions,
                    exported_keys=exported_keys,
                    use_external_pkey=use_external_pkey,
                )
                if related_records:
                    record[rel_key] = related_records

        return record if nested else self.db.typeConverter.toTypedJSON(record)

    def relatedSelectionToJson(self, field=None, value=None,
                               related_many='cascade',
                               dependencies=None, blacklist=None,
                               condition=None, condition_kwargs=None,
                               relation_conditions=None,
                               exported_keys=None,
                               use_external_pkey=None):
        """Fetch related records and convert to JSON (cycle-safe).

        :param field: foreign key field
        :param value: FK value to match
        :param related_many: cascade strategy
        :returns: list of JSON record dicts
        """
        related_json_list = []
        query_params = condition_kwargs or {}
        query_params = self.relatedQueryPars(
            where=condition, field=field, value=value, kwargs=query_params,
        )
        exported_keys = exported_keys or set()
        related_rows = self.query(
            columns=self.real_columns,
            subtable='*',
            ignorePartition=True,
            excludeDraft=False,
            excludeLogicalDeleted=False,
            addPkeyColumn=False,
            **query_params,
        ).fetch()
        for related_row in related_rows:
            related_key = f'{self.fullname}:{related_row[self.pkey]}'
            if related_key in exported_keys:
                continue
            related_record = dict(related_row)
            related_record_json = self.recordToJson(
                related_record,
                related_many=related_many,
                dependencies=dependencies,
                blacklist=blacklist,
                nested=True,
                relation_conditions=relation_conditions,
                exported_keys=exported_keys,
                use_external_pkey=use_external_pkey,
            )
            related_json_list.append(related_record_json)
        return related_json_list

    # ------------------------------------------------------------------
    #  XML
    # ------------------------------------------------------------------

    def toXml(self, pkeys=None, path=None, where=None, rowcaption=None,
              columns=None, related_one_dict=None, **kwargs):
        where = '$%s IN :pkeys' % self.pkey if pkeys else where
        columns = columns or '*'
        if rowcaption:
            rowcaption = (
                self.rowcaption if rowcaption is True else rowcaption
            )
            fields, mask = self.rowcaptionDecode(rowcaption)
            columns = '%s,%s' % (columns, ','.join(fields))
        f = self.query(
            where=where, pkeys=pkeys, columns=columns,
            bagFields=True, **kwargs,
        ).fetch()
        result = Bag()
        for r in f:
            caption = (
                self.recordCaption(record=r, rowcaption=rowcaption)
                if rowcaption else None
            )
            result.setItem(
                r[self.pkey], self.recordToXml(r),
                caption=caption, pkey=r[self.pkey],
            )
        if path:
            result.toXml(path, autocreate=True)
        return result

    def recordToXml(self, record, path=None):
        result = Bag()
        for col in self.columns:
            result[col] = record[col]
        if path:
            result.toXml(path, autocreate=True)
        return result

    @deprecated
    def xmlDump(self, path):
        """Dump all records to an XML file."""
        import os
        filepath = os.path.join(path, '%s_dump.xml' % self.name)
        records = self.query(
            excludeLogicalDeleted=False, excludeDraft=False,
        ).fetch()
        result = Bag()
        for r in records:
            r = dict(r)
            pkey = r.pop('pkey')
            result['records.%s' % pkey.replace('.', '_')] = Bag(r)
        result.toXml(filepath, autocreate=True)

    @deprecated
    def importFromXmlDump(self, path):
        """Import records from an XML dump file."""
        import os
        if '.xml' in path:
            filepath = path
        else:
            filepath = os.path.join(path, '%s_dump.xml' % self.name)
        data = Bag(filepath)
        if data:
            for record in list(data['records'].values()):
                record.pop('_isdeleted')
                self.insert(record)

    # ------------------------------------------------------------------
    #  Field comparison and aggregation
    # ------------------------------------------------------------------

    def fieldsChanged(self, fieldNames, record, old_record=None):
        """Return ``True`` if any field in *fieldNames* differs.

        :param fieldNames: comma-separated string or list
        """
        if isinstance(fieldNames, str):
            fieldNames = fieldNames.split(',')
        for field in fieldNames:
            if record.get(field) != old_record.get(field):
                return True
        return False

    def fieldAggregate(self, field, data, fieldattr=None, onSelection=False):
        handler = getattr(self, 'aggregate_%s' % field, None)
        if handler:
            return handler(data)
        dtype = fieldattr.get('dataType', None) or fieldattr.get('dtype', 'A')
        aggregator = fieldattr.get('aggregator')
        aggregator = (
            fieldattr.get('aggregator_record', aggregator)
            if not onSelection
            else fieldattr.get('aggregator_selection', aggregator)
        )
        if aggregator is False:
            return data
        if dtype == 'B':
            dd = [d or False for d in data]
            data = (
                not (False in dd)
                if (aggregator or 'AND') == 'AND'
                else (True in dd)
            )
        elif dtype in ('R', 'L', 'N'):
            aggregator = aggregator or 'SUM'
            dd = [r for r in data if r is not None]
            if not dd:
                data = None
            elif aggregator == 'SUM':
                data = sum(dd)
            elif aggregator == 'MAX':
                data = max(dd)
            elif aggregator == 'MIN':
                data = min(dd)
            elif aggregator == 'AVG':
                data = (sum(dd) / len(dd)) if len(dd) else 0
            elif aggregator == 'CNT':
                data = len(data) if data else 0
        else:
            data.sort(key=lambda x: MinValue if x is None else x)
            data = (aggregator or ',').join(
                uniquify([gnrstring.toText(d) for d in data]),
            )
        return data
