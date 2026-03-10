# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.crud : Insert, update, delete and batch operations
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

"""Insert, update, delete and batch operations.

Provides :class:`CrudMixin` — a mixin for :class:`~gnrsqltable.table.SqlTable`
containing the core CRUD methods (``insert``, ``update``, ``delete``),
raw variants, batch update, ``writeRecordCluster`` and related-record
cascade operations.
"""

from __future__ import annotations

import os

from gnr.core import gnrstring
from gnr.core.gnrbag import Bag

from gnr.sql._typing import SqlTableBaseMixin
from gnr.sql.gnrsqltable.helpers import (
    RecordUpdater,
    add_sql_comment,
    orm_audit_log,
)


class CrudMixin(SqlTableBaseMixin):
    """Insert, update, delete, batch and cluster operations."""

    # ------------------------------------------------------------------
    #  Simple CRUD
    # ------------------------------------------------------------------

    @add_sql_comment
    @orm_audit_log
    def insert(self, record, **kwargs):
        """Insert a single record.

        :param record: dict representing the record to insert
        """
        self.db.insert(self, record, **kwargs)
        return record

    @add_sql_comment
    @orm_audit_log
    def raw_insert(self, record, **kwargs):
        """Insert a single record without triggering hooks.

        :param record: dict representing the record to insert
        """
        self.db.raw_insert(self, record, **kwargs)
        return record

    @add_sql_comment
    @orm_audit_log
    def raw_delete(self, record, **kwargs):
        """Delete a single record without triggering hooks.

        :param record: dict representing the record to delete
        """
        self.db.raw_delete(self, record, **kwargs)

    @add_sql_comment
    @orm_audit_log
    def insertMany(self, records, **kwargs):
        self.db.insertMany(self, records, **kwargs)

    @add_sql_comment
    @orm_audit_log
    def raw_update(self, record=None, old_record=None, pkey=None, **kwargs):
        self.db.raw_update(
            self, record, old_record=old_record, pkey=pkey, **kwargs,
        )

    def changePrimaryKeyValue(self, pkey=None, newpkey=None, **kwargs):
        self.db.adapter.changePrimaryKeyValue(
            self, pkey=pkey, newpkey=newpkey,
        )

    @add_sql_comment
    @orm_audit_log
    def delete(self, record, **kwargs):
        """Delete a single record.

        :param record: dict, Bag or primary key string
        """
        if isinstance(record, str):
            record = self.record(
                pkey=record, for_update=True, ignoreMissing=True,
            ).output('dict')
            if not record:
                return
        self.db.delete(self, record, **kwargs)

    @add_sql_comment
    @orm_audit_log
    def update(self, record, old_record=None, pkey=None, **kwargs):
        """Update a single record.

        :param record: the new record data
        :param old_record: the previous record data
        :param pkey: primary key value
        """
        if old_record and not pkey:
            pkey = old_record.get(self.pkey)
        if record.get(self.pkey) == pkey:
            pkey = None
        packageStorename = self.pkg.attributes.get('storename')
        if packageStorename:
            with self.db.tempEnv(
                currentImplementation=self.dbImplementation,
                storename=packageStorename,
            ):
                self.db.update(
                    self, record, old_record=old_record,
                    pkey=pkey, **kwargs,
                )
        else:
            self.db.update(
                self, record, old_record=old_record,
                pkey=pkey, **kwargs,
            )
        return record

    # ------------------------------------------------------------------
    #  Related cascade
    # ------------------------------------------------------------------

    def updateRelated(self, record, old_record=None):
        for rel in self.relations_many:
            onUpdate = rel.getAttr('onUpdate', '').lower()
            if onUpdate and not (onUpdate in ('i', 'ignore')):
                mpkg, mtbl, mfld = rel.attr['many_relation'].split('.')
                opkg, otbl, ofld = rel.attr['one_relation'].split('.')
                if record.get(ofld) == old_record.get(ofld):
                    return
                relatedTable = self.db.table(mtbl, pkg=mpkg)
                sel = relatedTable.query(
                    columns='*',
                    where='%s = :pid' % mfld,
                    subtable='*',
                    excludeDraft=False,
                    ignorePartition=True,
                    excludeLogicalDeleted=False,
                    pid=old_record[ofld],
                    for_update=True,
                ).fetch()
                if sel:
                    if onUpdate in ('r', 'raise'):
                        raise self.exception(
                            'update', record=record,
                            msg='!!Record referenced in table %(reltable)s',
                            reltable=relatedTable.fullname,
                        )
                    if onUpdate in ('c', 'cascade'):
                        for row in sel:
                            rel_rec = dict(row)
                            rel_rec[mfld] = record[ofld]
                            relatedTable.update(rel_rec, old_record=dict(row))

    def deleteRelated(self, record):
        """Delete related records according to onDelete policy.

        :param record: the parent record being deleted
        """
        usingRootstore = self.db.usingRootstore()
        for rel in self.relations_many:
            defaultOnDelete = (
                'raise' if rel.getAttr('mode') == 'foreignkey' else 'ignore'
            )
            onDelete = rel.getAttr('onDelete', defaultOnDelete).lower()
            raiseMessage = '!!Record referenced in table %(reltable)s'
            if ':' in onDelete:
                onDelete, raiseMessage = onDelete.split(':')
            if onDelete and (onDelete not in ('i', 'ignore')):
                mpkg, mtbl, mfld = rel.attr['many_relation'].split('.')
                opkg, otbl, ofld = rel.attr['one_relation'].split('.')
                relatedTable = self.db.table(mtbl, pkg=mpkg)
                if (not usingRootstore
                        and relatedTable.use_dbstores() is False):
                    continue
                sel = relatedTable.query(
                    columns='*',
                    where='$%s = :pid' % mfld,
                    pid=record[ofld],
                    for_update=True,
                    subtable='*',
                    ignorePartition=True,
                    excludeDraft=False,
                    excludeLogicalDeleted=False,
                ).fetch()
                if sel:
                    if onDelete in ('r', 'raise'):
                        raise self.exception(
                            'delete', record=record,
                            msg=raiseMessage,
                            reltable=relatedTable.fullname,
                        )
                    elif onDelete in ('c', 'cascade'):
                        for row in self.db.quickThermo(sel):
                            relatedTable.delete(row)
                    elif onDelete in ('n', 'setnull'):
                        for row in self.db.quickThermo(sel):
                            rel_rec = dict(row)
                            rel_rec.pop('pkey', None)
                            oldrec = dict(rel_rec)
                            rel_rec[mfld] = None
                            relatedTable.update(rel_rec, oldrec)

    # ------------------------------------------------------------------
    #  Existence / duplicates
    # ------------------------------------------------------------------

    def existsRecord(self, record):
        """Check if *record* already exists in the table."""
        if not hasattr(record, 'keys'):
            record = {self.pkey: record}
        return self.db.adapter.existsRecord(self, record)

    def checkDuplicate(self, excludeDraft=None, ignorePartition=None,
                       **kwargs):
        where = ' AND '.join([
            '$%s=:%s' % (k, k) for k in kwargs.keys()
        ])
        return self.query(
            where=where, excludeDraft=excludeDraft,
            ignorePartition=ignorePartition, **kwargs,
        ).count() > 0

    def insertOrUpdate(self, record):
        """Insert *record* if it doesn't exist, else update it."""
        pkey = record.get(self.pkey)
        old_record = None
        if not (pkey in (None, '')):
            old_record = self.query(
                where="$%s=:pk" % self.pkey, pk=pkey, for_update=True,
            ).fetch()
        if not old_record:
            return self.insert(record)
        else:
            self.update(record, old_record=old_record[0])

    # ------------------------------------------------------------------
    #  Empty / fill
    # ------------------------------------------------------------------

    def empty(self, truncate=None):
        """Remove all rows from the table."""
        self.db.adapter.emptyTable(self, truncate=None)  # REVIEW: passes None instead of the truncate parameter

    def fillFromSqlTable(self, sqltablename):
        self.db.adapter.fillFromSqlTable(self, sqltablename)

    # ------------------------------------------------------------------
    #  Delete selection
    # ------------------------------------------------------------------

    def sql_deleteSelection(self, where=None, _pkeys=None, subtable=None,
                            **kwargs):
        """Delete rows by SQL (no Python triggers).

        :param where: WHERE clause
        """
        if where:
            todelete = self.query(
                '$%s' % self.pkey, where=where,
                addPkeyColumn=False, for_update=True,
                excludeDraft=False, _pkeys=_pkeys,
                subtable=subtable, **kwargs,
            ).fetch()
            _pkeys = [x[0] for x in todelete] if todelete else None
        if _pkeys:
            self.db.adapter.sql_deleteSelection(self, pkeyList=_pkeys)

    def deleteSelection(self, condition_field=None, condition_value=None,
                        excludeLogicalDeleted=False, excludeDraft=False,
                        condition_op='=', where=None, _wrapper=None,
                        _wrapperKwargs=None, **kwargs):
        """Delete a selection of records (with Python triggers).

        :param condition_field: field to filter on
        :param condition_value: value to match
        :param where: alternative WHERE clause
        """
        if condition_field and condition_value:
            where = '%s %s :condition_value' % (condition_field, condition_op)
            kwargs['condition_value'] = condition_value
        if not where:
            return
        q = self.query(
            where=where,
            excludeLogicalDeleted=excludeLogicalDeleted,
            addPkeyColumn=False, excludeDraft=excludeDraft,
            for_update=True, **kwargs,
        )
        sel = q.fetch()
        if _wrapper:
            _wrapperKwargs = _wrapperKwargs or dict()
            sel = _wrapper(sel, **(_wrapperKwargs or dict()))
        for r in sel:
            self.delete(r)
        return sel

    # ------------------------------------------------------------------
    #  Bag field expansion
    # ------------------------------------------------------------------

    def expandBagFields(self, record, columns=None):
        if not columns:
            columns = [
                k for k, v in list(self.model.columns.items())
                if v.dtype == 'X'
            ]
        if isinstance(columns, str):
            columns = columns.split(',')
        for c in columns:
            record[c] = Bag(record.get(c))

    # ------------------------------------------------------------------
    #  Batch update
    # ------------------------------------------------------------------

    def recordToUpdate(self, pkey=None, updater=None, **kwargs):
        """Return a :class:`RecordUpdater` context manager."""
        return RecordUpdater(self, pkey=pkey, **kwargs)

    def batchUpdate(self, updater=None, _wrapper=None, _wrapperKwargs=None,
                    autocommit=False, _pkeys=None, pkey=None,
                    _raw_update=None, _onUpdatedCb=None,
                    updater_kwargs=None, for_update=None,
                    deferredTotalize=None, **kwargs):
        """Batch-update rows matching *kwargs* query parameters.

        :param updater: a dict of values or a callable ``updater(row)``
        :param autocommit: commit after all updates
        """
        if 'where' not in kwargs:
            if pkey:
                _pkeys = [pkey]
            if not _pkeys:
                return
            kwargs['where'] = '$%s IN :_pkeys' % self.pkey
            if isinstance(_pkeys, str):
                _pkeys = _pkeys.strip(',').split(',')
            kwargs['_pkeys'] = _pkeys
            kwargs.setdefault('subtable', '*')
            kwargs.setdefault('excludeDraft', False)
            kwargs.setdefault('ignorePartition', True)
            kwargs.setdefault('excludeLogicalDeleted', False)
        elif pkey:
            kwargs['pkey'] = pkey
        fetch = self.query(
            addPkeyColumn=False, for_update=for_update or True, **kwargs,
        ).fetch()
        if _wrapper:
            _wrapperKwargs = _wrapperKwargs or dict()
            fetch = _wrapper(fetch, **(_wrapperKwargs or dict()))
        deferredTotalize = (
            set(deferredTotalize.split(',')) if deferredTotalize else None
        )
        with self.db.tempEnv(deferredTotalize=deferredTotalize):
            updatedKeys = self._batchUpdate_rows(
                rows=fetch, updater=updater,
                _raw_update=_raw_update,
                autocommit=autocommit,
                updater_kwargs=updater_kwargs,
                _onUpdatedCb=_onUpdatedCb,
            )
        if deferredTotalize:
            for t in deferredTotalize:
                self.db.table(t).realignRelatedTotalizers()
        return updatedKeys

    def _batchUpdate_rows(self, rows=None, updater=None, _raw_update=None,
                          autocommit=None, updater_kwargs=None,
                          _onUpdatedCb=None):
        updatedKeys = []
        pkeycol = self.pkey
        updatercb, updaterdict = None, None
        commit_every = False
        if autocommit and autocommit is not True:
            commit_every = autocommit
            autocommit = False
        if callable(updater):
            if updater_kwargs:
                def updatercb(row):
                    return updater(row, **updater_kwargs)
            else:
                updatercb = updater
        elif isinstance(updater, dict):
            updaterdict = updater
        for i, row in enumerate(rows):
            new_row = dict(row)
            if not _raw_update:
                self.expandBagFields(row)
                self.expandBagFields(new_row)
            if updatercb:
                doUpdate = updatercb(new_row)
                if doUpdate is False:
                    continue
            elif updaterdict:
                new_row.update(updater)
            record_pkey = row[pkeycol]
            updatedKeys.append(record_pkey)
            if not _raw_update:
                self.update(new_row, row, pkey=record_pkey)
            else:
                self.raw_update(new_row, old_record=row, pkey=record_pkey)
            if _onUpdatedCb:
                _onUpdatedCb(
                    record=new_row, old_record=row, pkey=record_pkey,
                )
            if commit_every and i % commit_every == 0:
                self.db.commit()
        if autocommit:
            self.db.commit()
        return updatedKeys

    # ------------------------------------------------------------------
    #  Set / read columns helpers
    # ------------------------------------------------------------------

    def setColumns(self, pkey, **kwargs):
        record = self.record(pkey, for_update=True).output('dict')
        old_record = dict(record)
        for k, v in list(kwargs.items()):
            if record[k] != v:
                record[k] = v
        if record != old_record:
            self.update(record, old_record)

    def readColumns(self, pkey=None, columns=None, where=None,
                    subtable='*', **kwargs):
        """Read specific columns for a single record.

        :param pkey: primary key
        :param columns: columns to read
        :param where: optional WHERE clause
        """
        where = where or '$%s=:pkey' % self.pkey
        kwargs.pop('limit', None)
        kwargs.setdefault('ignoreTableOrderBy', True)
        fetch = self.query(
            columns=columns, limit=1, where=where,
            pkey=pkey, addPkeyColumn=False, excludeDraft=False,
            ignorePartition=True, excludeLogicalDeleted=False,
            subtable=subtable, **kwargs,
        ).fetch()
        if not fetch:
            row = [None for x in columns.split(',')]
        else:
            row = fetch[0]
        if len(row) == 1:
            row = row[0]
        return row

    # ------------------------------------------------------------------
    #  Count / lock
    # ------------------------------------------------------------------

    def countRecords(self):
        return self.query(
            excludeLogicalDeleted=False, excludeDraft=False,
        ).count()

    def lock(self, mode='ACCESS EXCLUSIVE', nowait=False):
        """Acquire a table-level lock.

        :param mode: lock mode
        :param nowait: if ``True``, fail immediately if lock unavailable
        """
        self.db.adapter.lockTable(self, mode, nowait)

    # ------------------------------------------------------------------
    #  Write record cluster
    # ------------------------------------------------------------------

    def writeRecordCluster(self, recordCluster, recordClusterAttr,
                           debugPath=None):
        """Process a client changeset and execute insert/delete/update.

        :param recordCluster: Bag with the record changes
        :param recordClusterAttr: dict of cluster metadata
        :param debugPath: optional path for XML debug dumps
        """
        main_changeSet, relatedOne, relatedMany = self._splitRecordCluster(
            recordCluster, debugPath=debugPath,
        )
        isNew = recordClusterAttr.get('_newrecord')
        toDelete = recordClusterAttr.get('_deleterecord')
        pkey = recordClusterAttr.get('_pkey')
        invalidFields = recordClusterAttr.get('_invalidFields')
        noTestForMerge = (
            self.attributes.get('noTestForMerge')
            or self.pkg.attributes.get('noTestForMerge')
        )
        blackListAttributes = ('__old', '_newrecord')
        if isNew and toDelete:
            return
        if isNew:
            main_record = main_changeSet
        else:
            old_record = self.record(
                pkey, for_update=True, bagFields=True,
            ).output('bag', resolver_one=False, resolver_many=False)
            main_record = old_record.deepcopy()
            if main_changeSet or toDelete:
                lastTs = recordClusterAttr.get('lastTS')
                changed_TS = lastTs and (
                    lastTs != str(main_record[self.lastTS])
                )
                if changed_TS and (self.noChangeMerge or toDelete):
                    raise self.exception(
                        "save", record=main_record,
                        msg=(
                            "Another user modified the record."
                            "Operation aborted changed_TS %s  lastTs %s "
                            % (changed_TS, lastTs)
                        ),
                    )
                if toDelete:
                    self.delete(old_record)
                    return
                testForMerge = not noTestForMerge and (
                    changed_TS or (not lastTs)
                )
                for fnode in main_changeSet:
                    fname = fnode.label
                    if testForMerge:
                        incompatible = False
                        if fnode.getAttr('_gnrbag'):
                            pass
                        elif fnode.value != main_record[fname]:
                            incompatible = (
                                fnode.getAttr('oldValue')
                                != main_record[fname]
                            )
                        if incompatible:
                            raise self.exception(
                                "save", record=main_record,
                                msg=(
                                    "Incompatible changes: another user "
                                    "modified field %(fldname)s from "
                                    "%(oldValue)s to %(newValue)s"
                                ),
                                fldname=fname,
                                oldValue=fnode.getAttr('oldValue'),
                                newValue=main_record[fname],
                            )
                    main_record[fname] = fnode.value

        for rel_name, rel_recordClusterNode in list(relatedOne.items()):
            rel_recordCluster = rel_recordClusterNode.value
            rel_recordClusterAttr = rel_recordClusterNode.getAttr()
            rel_column = self.model.column(rel_name)
            rel_tblobj = rel_column.relatedTable().dbtable
            joiner = rel_column.relatedColumnJoiner()
            rel_record = rel_tblobj.writeRecordCluster(
                rel_recordCluster, rel_recordClusterAttr,
            )
            from_fld = joiner['many_relation'].split('.')[2]
            to_fld = joiner['one_relation'].split('.')[2]
            main_record[from_fld] = rel_record[to_fld]
            recordClusterAttr['lastTS_%s' % rel_name] = (
                str(rel_record[rel_tblobj.lastTS])
                if rel_tblobj.lastTS else None
            )

        if self.attributes.get('invalidFields'):
            invalidFields_fld = self.attributes.get('invalidFields')
            main_record[invalidFields_fld] = (
                gnrstring.toJsonJS(invalidFields) if invalidFields else None
            )

        if isNew:
            self.insert(
                main_record, blackListAttributes=blackListAttributes,
            )
        elif main_changeSet:
            self.update(
                main_record, old_record=old_record, pkey=pkey,
                blackListAttributes=blackListAttributes,
            )

        for rel_name, rel_recordClusterNode in list(relatedMany.items()):
            rel_recordCluster = rel_recordClusterNode.value
            rel_recordClusterAttr = rel_recordClusterNode.getAttr()
            if rel_name.endswith('_removed'):
                rel_name = rel_name[:-8]
            relblock = self.model.getRelationBlock(rel_name)
            many_tblobj = self.db.table(
                relblock['mtbl'], pkg=relblock['mpkg'],
            )
            many_key = relblock['mfld']
            relKey = main_record[relblock['ofld']]
            if rel_recordClusterAttr.get('one_one', None):
                rel_recordCluster[many_key] = relKey
                many_tblobj.writeRecordCluster(
                    rel_recordCluster, rel_recordClusterAttr,
                )
            else:
                for sub_recordClusterNode in rel_recordCluster:
                    if (sub_recordClusterNode.attr.get('_newrecord')
                            and not sub_recordClusterNode.attr.get(
                                '_deleterecord')):
                        sub_recordClusterNode.value[many_key] = relKey
                    many_tblobj.writeRecordCluster(
                        sub_recordClusterNode.value,
                        sub_recordClusterNode.getAttr(),
                    )
        return main_record

    def xmlDebug(self, data, debugPath, name=None):
        """Dump *data* as XML for debugging.

        :param data: Bag to serialize
        :param debugPath: directory path
        :param name: filename base (defaults to table name)
        """
        name = name or self.name
        filepath = os.path.join(debugPath, '%s.xml' % name)
        data.toXml(filepath, autocreate=True)

    def _splitRecordCluster(self, recordCluster, mainRecord=None,
                            debugPath=None):
        relatedOne = {}
        relatedMany = {}
        if recordCluster:
            nodes = recordCluster.nodes
            revnodes = list(enumerate(nodes))
            revnodes.reverse()
            for j, n in revnodes:
                if n.label.startswith('@'):
                    if n.getAttr('mode') == 'O':
                        relatedOne[n.label[1:]] = nodes.pop(j)
                    else:
                        relatedMany[n.label] = nodes.pop(j)
        if debugPath:
            self.xmlDebug(recordCluster, debugPath)
            for k, v in list(relatedOne.items()):
                self.xmlDebug(v, debugPath, k)
            for k, v in list(relatedMany.items()):
                self.xmlDebug(v, debugPath, k)
        return recordCluster, relatedOne, relatedMany

    # ------------------------------------------------------------------
    #  Field triggers (internal)
    # ------------------------------------------------------------------

    def _doFieldTriggers(self, triggerEvent, record, **kwargs):
        trgFields = self.model._fieldTriggers.get(triggerEvent)
        if trgFields:
            for fldname, trgFunc, trigger_table in trgFields:
                if callable(trgFunc):
                    trgFunc(record, fldname)
                else:
                    ttable = (
                        self if not trigger_table
                        else self.db.table(trigger_table)
                    )
                    getattr(ttable, 'trigger_%s' % trgFunc)(
                        record, fldname=fldname,
                        tblname=self.fullname, **kwargs,
                    )

    def _doExternalPkgTriggers(self, triggerEvent, record, **kwargs):
        if not self.db.application:
            return
        for pkg_id in list(self.db.application.packages.keys()):
            trigger_name = 'trigger_%s_%s' % (triggerEvent, pkg_id)
            avoid_trigger_par = self.db.currentEnv.get(
                'avoid_trigger_%s' % pkg_id,
            )
            if avoid_trigger_par:
                if (avoid_trigger_par == '*'
                        or triggerEvent in avoid_trigger_par.split(',')):
                    continue
            trgFunc = getattr(self, trigger_name, None)
            if callable(trgFunc):
                trgFunc(record, **kwargs)
