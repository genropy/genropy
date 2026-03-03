# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.copy : Record copy, paste, duplicate and archive
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

"""Record copy, paste, duplicate and archive operations.

Provides :class:`CopyMixin` — a mixin for
:class:`~gnrsqltable.table.SqlTable` that handles clipboard-style
copy/paste, record duplication (single and recursive), and archival
of related cascade records.
"""

from __future__ import annotations

from gnr.core.gnrdecorator import public_method
from gnr.sql._typing import SqlTableBaseMixin


class CopyMixin(SqlTableBaseMixin):
    """Record copy, paste, duplicate and archive operations."""

    # ------------------------------------------------------------------
    #  Items as text
    # ------------------------------------------------------------------

    def itemsAsText(self, caption_field=None, cols=None, **kwargs):
        """Return table items as a text string for use in combo fields.

        :param caption_field: field to use as caption
        :param cols: number of items per line (separated by ``/``)
        """
        caption_field = caption_field or self.attributes['caption_field']
        f = self.query(
            columns='$%s,$%s' % (self.pkey, caption_field), **kwargs,
        ).fetch()
        l = []
        for i, r in enumerate(f):
            if cols and i and not i % cols:
                l.append('/')
            l.append(
                '%s:%s' % (
                    r[self.pkey],
                    r[caption_field].replace(',', ' ').replace(':', ' '),
                ),
            )
        return ','.join(l)

    # ------------------------------------------------------------------
    #  Archive
    # ------------------------------------------------------------------

    def onArchivingRecord(self, record=None, archive_ts=None):
        """Hook called when a record is being archived.

        :param record: the record being archived
        :param archive_ts: timestamp for the archive operation
        """
        self.archiveRelatedRecords(record=record, archive_ts=archive_ts)

    def archiveRelatedRecords(self, record=None, archive_ts=None):
        """Archive cascade-related records by setting their logical deletion field.

        :param record: the parent record
        :param archive_ts: timestamp to set on logically deleted records
        """
        usingRootstore = self.db.usingRootstore()
        for rel in self.relations_many:
            if rel.getAttr('onDelete', 'raise').lower() == 'cascade':
                mpkg, mtbl, mfld = rel.attr['many_relation'].split('.')
                opkg, otbl, ofld = rel.attr['one_relation'].split('.')
                relatedTable = self.db.table(mtbl, pkg=mpkg)
                if not usingRootstore and relatedTable.use_dbstores() is False:
                    continue
                if relatedTable.logicalDeletionField:
                    updater = {relatedTable.logicalDeletionField: archive_ts}
                    relatedTable.batchUpdate(
                        updater,
                        where='$%s = :pid' % mfld,
                        pid=record[ofld],
                        excludeDraft=False,
                        excludeLogicalDeleted=False,
                    )

    # ------------------------------------------------------------------
    #  Copy / Paste
    # ------------------------------------------------------------------

    @public_method
    def onCopyRecord(self, pkey=None):
        """Copy a record (with cascade relations) to a Bag for pasting.

        :param pkey: primary key of the record to copy
        :returns: a Bag representing the copied record cluster
        """
        record = self.record(pkey).output('bag', resolver_one=False)
        _pathlist = []
        nodes_to_del = []

        def _onCopyRecord_expandNode(node, _pathlist=None, **kwargs):
            if node.resolver is not None:
                node.attr.pop('js_resolver', None)
                node.attr.pop('_resolver_kwargs', None)
                node.attr.pop('_resolver_name', None)
                if (
                    node.attr.get('mode') == 'M'
                    and node.attr.get('_onDelete') == 'cascade'
                ):
                    return self.db.table(
                        '.'.join(
                            node.attr.get('_target_fld').split('.')[:2],
                        ),
                    )._onCopyExpandMany(node)
                else:
                    nodes_to_del.append(
                        '.'.join(_pathlist + [node.label]),
                    )

        record.walk(
            _onCopyRecord_expandNode, _mode='static', _pathlist=_pathlist,
        )
        for p in nodes_to_del:
            record.popNode(p)
        return record

    def _onCopyExpandMany(self, node):
        """Expand a many-relation node during copy.

        :param node: the Bag node to expand
        """
        if (
            self.attributes.get('hierarchical_linked_to')
            and node.label == '@_children'
        ):
            node.resolver = None
            node._value = None
            return False
        node.resolver.readOnly = False
        for n in node.getValue():
            n.resolver.readOnly = False
            n.value
            n.resolver = None
        node.resolver = None

    @public_method
    def onPasteRecord(self, sourceCluster=None, **kwargs):
        """Paste a previously copied record cluster.

        :param sourceCluster: the Bag from ``onCopyRecord``
        :returns: the primary key of the inserted record
        """
        result = self.insertPastedCluster(
            sourceCluster=sourceCluster, **kwargs,
        )
        self.db.commit()
        return result[self.pkey]

    def insertPastedCluster(self, sourceCluster, **kwargs):
        """Insert a pasted record cluster recursively.

        :param sourceCluster: Bag representing the record and its relations
        :returns: the inserted record
        """
        destrecord = self.newrecord(_fromRecord=sourceCluster, **kwargs)
        self.insert(destrecord)
        for node in sourceCluster:
            if node.attr.get('mode') != 'M':
                continue
            l = node.attr['_target_fld'].split('.')
            reltblobj = self.db.table('.'.join(l[:2]))
            reltblobj._onPasteExpandeMany(
                node, **{l[2]: destrecord[self.pkey]},
            )
        return destrecord

    def _onPasteExpandeMany(self, node, **kwargs):
        """Expand and paste a many-relation node.

        :param node: the Bag node representing related records
        """
        if self.attributes.get('hierarchical_linked_to'):
            fkeyCol = node.attr.get('_target_fld').split('.')[2]
            if self.column(fkeyCol).attributes.get('fkeyToMaster'):
                self._duplicateLinkedTree(node, **kwargs)
                return
        if node.value is None:
            return
        for r in node.value.values():
            self.insertPastedCluster(sourceCluster=r, **kwargs)

    def _duplicateLinkedTree(self, node, **kwargs):
        """Duplicate a hierarchical linked tree during paste.

        :param node: the Bag node representing the tree
        """
        fkeyCol = node.attr.get('_target_fld').split('.')[2]
        fkeyValue = kwargs[fkeyCol]
        value = node.value
        newroot = self.record(fkeyValue).output('dict')
        values = list(value.values())
        copydict = {values[0][self.pkey]: newroot[self.pkey]}
        for rec in values[1:]:
            dupkwargs = dict(kwargs)
            for k, v in rec.items():
                if not isinstance(v, str):
                    continue
                if v in copydict:
                    dupkwargs[k] = copydict[v]
            copied_record = self.insertPastedCluster(
                sourceCluster=rec, **dupkwargs,
            )
            copydict[rec[self.pkey]] = copied_record[self.pkey]

    @public_method
    def onCopySelection(self, pkeys=None):
        """Hook for copying a selection of records.

        :param pkeys: list of primary keys
        """
        pass

    @public_method
    def onPasteSelection(self, records=None):
        """Hook for pasting a selection of records.

        :param records: list of record dicts
        """
        pass

    # ------------------------------------------------------------------
    #  Duplicate
    # ------------------------------------------------------------------

    def duplicateRecord(self, recordOrKey=None, howmany=None,
                        destination_store=None, **kwargs):
        """Duplicate a record (and optionally its cascade relations).

        :param recordOrKey: record dict or primary key
        :param howmany: number of copies or comma-separated labels
        :param destination_store: optional target dbstore
        :returns: the first duplicated record
        """
        duplicatedRecords = []
        howmany = howmany or 1
        howmany = str(howmany)
        original_record = self.recordAs(recordOrKey, mode='dict')
        original_pkey = original_record.get(self.pkey, None)
        record = dict(original_record)
        record[self.pkey] = None
        for colname, obj in self.model.columns.items():
            if (colname == self.draftField) or (colname == 'parent_id'):
                continue
            if (
                obj.attributes.get('unique')
                or obj.attributes.get('_sysfield')
            ):
                record[colname] = None
        self.onDuplicating(record)
        if howmany.isdigit():
            labels = [str(k) for k in range(int(howmany))]
        else:
            labels = howmany.split(',')
        for i, label in enumerate(labels):
            r = dict(record)
            r.update(kwargs)
            self.onDuplicating_many(r, copy_number=i, copy_label=label)
            if destination_store:
                with self.db.tempEnv(storename=destination_store):
                    self.insert(r)
            else:
                self.insert(r)
            duplicatedRecords.append(r)
        for n in self.model.relations:
            joiner = n.attr.get('joiner', {})
            onDuplicate = joiner.get('onDuplicate')
            if onDuplicate is None and (
                joiner.get('onDelete') == 'cascade'
                or joiner.get('onDelete_sql') == 'cascade'
            ):
                onDuplicate = 'recursive'
            if (
                joiner
                and joiner['mode'] == 'M'
                and onDuplicate == 'recursive'
            ):
                rellist = joiner['many_relation'].split('.')
                fkey = rellist[-1]
                subtable = '.'.join(rellist[:-1])
                manytable = self.db.table(subtable)
                rows = manytable.getRowsForDuplication(
                    original_pkey, fkey=fkey,
                )
                for dupRec in duplicatedRecords:
                    for r in rows:
                        r = dict(r)
                        r[fkey] = dupRec[self.pkey]
                        manytable.duplicateRecord(
                            r, destination_store=destination_store,
                        )
        self.onDuplicated(
            duplicated_records=duplicatedRecords,
            original_record=original_record,
        )
        return duplicatedRecords[0]

    def onDuplicating(self, record, **kwargs):
        """Hook called before duplicating — modify *record* fields as needed.

        :param record: the record about to be duplicated
        """
        pass

    def onDuplicating_many(self, r, copy_number=None, copy_label=None,
                           **kwargs):
        """Hook called for each copy when duplicating multiple.

        :param r: the record copy
        :param copy_number: zero-based copy index
        :param copy_label: label for this copy
        """
        pass

    def onDuplicated(self, duplicated_records=None, original_record=None,
                     **kwargs):
        """Hook called after duplication is complete.

        :param duplicated_records: list of duplicated record dicts
        :param original_record: the original record
        """
        pass

    def getRowsForDuplication(self, master_original_pkey=None, fkey=None):
        """Fetch rows to duplicate for a given master record.

        :param master_original_pkey: pkey of the master record
        :param fkey: foreign key field linking to master
        :returns: fetched rows
        """
        return self.query(
            where=f"${fkey}=:p",
            p=master_original_pkey,
            addPkeyColumn=False,
            bagFields=True,
        ).fetch()
