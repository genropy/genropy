# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.utils : Utility methods, data export, totalizers
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

"""Utility methods: pkey generation, data export, totalizers, retention.

Provides :class:`UtilsMixin` — a mixin for
:class:`~gnrsqltable.table.SqlTable` that contains infrastructure helpers
such as primary-key generation, cross-database copy, relation exploration,
totalizer management and data retention policies.
"""

from __future__ import annotations

import functools
from datetime import datetime, timedelta

import pytz

from gnr.core import gnrstring
from gnr.core.gnrlang import getUuid
from gnr.core.gnrbag import Bag, BagCbResolver
from gnr.core.gnrdict import dictExtract
from gnr.sql import logger
from gnr.sql._typing import SqlTableBaseMixin


class UtilsMixin(SqlTableBaseMixin):
    """Utility methods: pkey generation, data export, totalizers, retention."""

    # ------------------------------------------------------------------
    #  System records
    # ------------------------------------------------------------------

    def createSysRecords(self):
        """Hook to create system records during table initialization."""
        pass

    def cleanWrongSysRecordPkeys(self):
        """Re-compute and fix primary keys for system records."""
        f = self.query(
            for_update=True, where='$__syscode IS NOT NULL',
        ).fetch()
        for row in f:
            old_r = dict(row)
            validpkey = self.pkeyValue(row)
            currpkey = row[self.model.pkey]
            if currpkey != validpkey:
                row[self.pkey] = validpkey
                self.update(row, old_r, pkey=currpkey)
                self.db.commit()

    # ------------------------------------------------------------------
    #  Primary key helpers
    # ------------------------------------------------------------------

    def newPkeyValue(self, record=None):
        """Get a new unique id for use as primary key.

        :param record: the record being inserted (used for composite keys)
        """
        return self.pkeyValue(record=record)

    def compositeKey(self, record=None, field=None):
        """Generate a composite key value from *record* fields.

        :param record: the record dict
        :param field: the composite key field name
        """
        return self.db.typeConverter.toTypedJSON(
            [record[key] for key in self.column(field).composed_of.split(',')],
        )

    def pkeyValue(self, record=None):
        """Compute the primary key value for a record.

        Handles composite keys, numeric auto-increment, UUID generation,
        ``pkey_columns`` concatenation and ``__syscode`` based keys.

        :param record: the record dict (optional)
        """
        if len(self.pkeys) > 1:
            return self.compositeKey(record, field=self.pkey)
        pkeyfield = self.model.pkey
        pkeycol = self.model.column(pkeyfield)
        if pkeycol.dtype in ('L', 'I', 'R'):
            lastid = self.query(
                columns=f'max(${pkeyfield})', group_by='*',
            ).fetch()[0]
            return (lastid[0] or 0) + 1
        elif not record:
            return getUuid()
        elif self.attributes.get('pkey_columns'):
            joiner = self.attributes.get('pkey_columns_joiner') or '_'
            return joiner.join([
                str(record.get(col))
                for col in self.attributes.get('pkey_columns').split(',')
                if record.get(col) is not None
            ])
        elif record.get('__syscode'):
            sysparscb = getattr(
                self, f'sysRecord_{record["__syscode"]}', None,
            )
            syspars = sysparscb() if sysparscb else {}
            if syspars.get(pkeyfield):
                return syspars[pkeyfield]
            size = pkeycol.getAttr('size')
            if size and ':' not in size:
                return record['__syscode'].ljust(int(size), '_')
            else:
                return record['__syscode']
        elif (
            pkeycol.dtype in ('T', 'A', 'C')
            and pkeycol.attributes.get('size') in ('22', ':22', None)
        ):
            return getUuid()

    def newUTCDatetime(self, delta_minutes=None):
        """Return a UTC-aware datetime, optionally offset.

        :param delta_minutes: minutes to add to current UTC time
        """
        utc_tz = pytz.timezone('UTC')
        utc_dt = datetime.now(utc_tz)
        if delta_minutes:
            utc_dt += timedelta(minutes=delta_minutes)
        return utc_dt

    # ------------------------------------------------------------------
    #  Resource / init hooks
    # ------------------------------------------------------------------

    def getResource(self, path):
        """Load a table resource by *path*.

        :param path: resource path
        """
        return self.db.getResource(self, path)

    def onIniting(self):
        """Hook called during table initialization (before ``onInited``)."""
        pass

    def onInited(self):
        """Hook called after table initialization is complete."""
        pass

    # ------------------------------------------------------------------
    #  Dependencies
    # ------------------------------------------------------------------

    def dependenciesTree(self, records=None, history=None, ascmode=False):
        """Build a dependency tree for a set of records.

        Traverses both outgoing (one) and incoming (many) relations
        to collect all dependent records.

        :param records: list of record dicts
        :param history: accumulator dict (used in recursion)
        :param ascmode: if ``True``, traversing ascending relations
        :returns: dict mapping table names to sets of pkeys
        """
        history = history or dict()
        for rel in self.relations_one:
            mpkg, mtbl, mfld = rel.attr['many_relation'].split('.')
            opkg, otbl, ofld = rel.attr['one_relation'].split('.')
            if not rel.attr.get('foreignkey'):
                continue
            relatedTable = self.db.table(otbl, pkg=opkg)
            tablename = relatedTable.fullname
            if tablename not in history:
                history[tablename] = dict(one=set(), many=set())
            one_history_set = history[tablename]['one']
            sel = relatedTable.query(
                columns=relatedTable.real_columns,
                where='$%s IN :pkeys' % ofld,
                pkeys=list(
                    set([r[mfld] for r in records]) - one_history_set,
                ),
                excludeDraft=False,
                excludeLogicalDeleted=False,
                subtable='*',
                ignorePartition=True,
            ).fetch()
            if sel:
                one_history_set.update(
                    [r[relatedTable.pkey] for r in sel],
                )
                relatedTable.dependenciesTree(
                    sel, history=history, ascmode=True,
                )

        for rel in self.relations_many:
            mpkg, mtbl, mfld = rel.attr['many_relation'].split('.')
            opkg, otbl, ofld = rel.attr['one_relation'].split('.')
            relatedTable = self.db.table(mtbl, pkg=mpkg)
            tablename = relatedTable.fullname
            if tablename not in history:
                history[tablename] = dict(one=set(), many=set())
            if ascmode and not (
                len(relatedTable.relations_one) == 1
                and len(relatedTable.relations_many) == 0
                and relatedTable.relations_one.getAttr(
                    '#0', 'onDelete',
                ) == 'cascade'
            ):
                continue
            many_history_set = history[tablename]['many']
            sel = relatedTable.query(
                columns=relatedTable.real_columns,
                where=(
                    '$%s in :rkeys AND $%s NOT IN :pklist'
                    % (mfld, relatedTable.pkey)
                ),
                pklist=list(many_history_set),
                rkeys=[r[ofld] for r in records],
                excludeDraft=False,
                excludeLogicalDeleted=False,
                subtable='*',
                ignorePartition=True,
            ).fetch()
            if sel:
                many_history_set.update(
                    [r[relatedTable.pkey] for r in sel],
                )
                relatedTable.dependenciesTree(
                    sel, history=history, ascmode=False,
                )

        return history

    # ------------------------------------------------------------------
    #  Cross-database copy / export / import
    # ------------------------------------------------------------------

    def copyToDb(self, dbsource, dbdest, empty_before=False,
                 excludeLogicalDeleted=False, excludeDraft=False,
                 source_records=None, bagFields=True,
                 source_tbl_name=None, raw_insert=None,
                 _converters=None, **querykwargs):
        """Copy records from one database to another.

        :param dbsource: source database
        :param dbdest: destination database
        :param empty_before: if ``True``, empty dest table first
        :param source_records: pre-fetched records (optional)
        :param raw_insert: if ``True``, use ``raw_insert``
        """
        tbl_name = self.fullname
        source_tbl = dbsource.table(source_tbl_name or tbl_name)
        dest_tbl = dbdest.table(tbl_name)
        querykwargs['addPkeyColumn'] = False
        querykwargs['excludeLogicalDeleted'] = excludeLogicalDeleted
        querykwargs['excludeDraft'] = excludeDraft
        source_records = (
            source_records
            or source_tbl.query(bagFields=bagFields, **querykwargs).fetch()
        )
        insertOnly = False
        if empty_before:
            insertOnly = True
            dest_tbl.empty()
        elif raw_insert and dest_tbl.countRecords() == 0:
            insertOnly = True
        for record in source_records:
            record = dict(record)
            if _converters:
                for c in _converters:
                    record = getattr(self, c)(record)
            if insertOnly:
                if raw_insert:
                    dest_tbl.raw_insert(record)
                else:
                    dest_tbl.insert(record)
            else:
                dest_tbl.insertOrUpdate(record)

    def copyToDbstore(self, pkey=None, dbstore=None, bagFields=True,
                      empty_before=False, **kwargs):
        """Copy records to a named dbstore.

        :param pkey: optional single pkey to copy
        :param dbstore: target store name
        :param empty_before: if ``True``, empty target first
        """
        queryargs = kwargs
        if pkey:
            queryargs = dict(where='$pkey=:pkey', pkey=pkey)
        records = self.query(
            addPkeyColumn=False, bagFields=bagFields, **queryargs,
        ).fetch()
        with self.db.tempEnv(storename=dbstore):
            if empty_before:
                self.empty()
            for rec in records:
                self.insertOrUpdate(rec)

    def exportToAuxInstance(self, instance, empty_before=False,
                            excludeLogicalDeleted=True,
                            excludeDraft=True, source_records=None,
                            **querykwargs):
        """Export records to an auxiliary application instance.

        :param instance: instance name or object
        :param empty_before: if ``True``, empty dest table first
        """
        if isinstance(instance, str):
            instance = self.db.application.getAuxInstance(instance)
        dest_db = instance.db
        self.copyToDb(
            self.db, dest_db,
            empty_before=empty_before,
            excludeLogicalDeleted=excludeLogicalDeleted,
            excludeDraft=True,
            source_records=source_records,
            **querykwargs,
        )

    def importFromAuxInstance(self, instance, empty_before=False,
                              excludeLogicalDeleted=False,
                              excludeDraft=False, source_records=None,
                              source_tbl_name=None, raw_insert=None,
                              **querykwargs):
        """Import records from an auxiliary application instance.

        Handles version conversion if source and destination table
        versions differ.

        :param instance: instance name or object
        :param empty_before: if ``True``, empty dest table first
        :param source_tbl_name: optional source table name override
        :param raw_insert: if ``True``, use ``raw_insert``
        """
        if isinstance(instance, str):
            instance = self.db.application.getAuxInstance(instance)
        source_db = instance.db
        src_version = int(
            source_db.table(
                source_tbl_name or self.fullname,
            ).attributes.get('version') or 0,
        )
        dest_version = int(self.attributes.get('version') or 0)
        converters = None
        if src_version != dest_version:
            assert dest_version > src_version, (  # REVIEW: assert for runtime validation — disabled with python -O
                'table %s version conflict from %i to %i'
                % (self.fullname, src_version, dest_version)
            )
            converters = [
                '_convert_%i_%i' % (x, x + 1)
                for x in range(src_version, dest_version)
            ]
            if [m for m in converters if not hasattr(self, m)]:
                logger.warning('Missing converter %s', self.fullname)
                return
        self.copyToDb(
            source_db, self.db,
            empty_before=empty_before,
            excludeLogicalDeleted=excludeLogicalDeleted,
            source_records=source_records,
            excludeDraft=excludeDraft,
            raw_insert=raw_insert,
            source_tbl_name=source_tbl_name,
            _converters=converters,
            **querykwargs,
        )

    # ------------------------------------------------------------------
    #  Releases
    # ------------------------------------------------------------------

    def getReleases(self):
        """Collect ``_release_N`` methods and return updaters and extra columns.

        :returns: tuple of ``(parslist, extra_columns_string)``
        """
        prefix = '_release_'
        parslist = []
        extra_columns_list = []
        for fname in sorted(dir(self)):
            if fname.startswith(prefix):
                handler = getattr(self, fname)
                assert (int(fname[9:]) == len(parslist) + 1), (
                    'Missing release'
                )
                pars = handler()
                updater = pars.pop('updater')
                extra_columns = pars.pop('extra_columns', None)
                if extra_columns:
                    extra_columns_list.extend(extra_columns.split(','))
                parslist.append((updater, pars))
        return parslist, ','.join(set(extra_columns_list))

    def updateRecordsToLastRelease_raw(self, commit=None,
                                        _wrapper=None,
                                        _wrapperKwargs=None):
        """Update all records to the latest release using raw updates.

        :param commit: if truthy, commit; if int, commit every N records
        """
        releases, extra_columns = self.getReleases()
        if not releases:
            return
        release = len(releases)
        toupdate = self.query(
            columns='*,%s' % extra_columns,
            where='$__release IS NULL OR $__release < :release',
            release=release,
            for_update=True,
            excludeLogicalDeleted=False,
            excludeDraft=False,
        ).fetch()
        if _wrapper:
            _wrapperKwargs = _wrapperKwargs or dict()
            toupdate = _wrapper(toupdate, **(_wrapperKwargs or dict()))
        commit_frequency = (
            commit if commit and isinstance(commit, int) else None
        )
        n = 0
        for record in toupdate:
            record = dict(record)
            oldrecord = dict(record)
            record_release = record['__release'] or 0
            for updater, kwargs in releases[record_release:]:
                updater(record, **kwargs)
            record['__release'] = release
            self.raw_update(record, oldrecord)
            if commit_frequency and n % commit_frequency == 0:
                self.db.commit()
            n += 1
        if commit:
            self.db.commit()

    # ------------------------------------------------------------------
    #  Relation explorer
    # ------------------------------------------------------------------

    def relationExplorer(self, omit='', prevRelation='', dosort=True,
                         pyresolver=False, relationStack='',
                         checkPermissions=None, **kwargs):
        """Build a Bag describing all relations for UI exploration.

        :param omit: group codes to omit
        :param prevRelation: prefix for nested relation paths
        :param dosort: if ``True``, sort by group
        :param pyresolver: if ``True``, attach lazy resolvers
        :param checkPermissions: permission check kwargs
        :returns: a Bag with relation metadata
        """
        def xvalue(attributes):
            if not pyresolver:
                return
            if attributes.get('one_relation'):
                if attributes['mode'] == 'O':
                    relpkg, reltbl, relfld = (
                        attributes['one_relation'].split('.')
                    )
                else:
                    relpkg, reltbl, relfld = (
                        attributes['many_relation'].split('.')
                    )
                targettbl = self.db.table('%s.%s' % (relpkg, reltbl))
                return BagCbResolver(
                    targettbl.relationExplorer, omit=omit,
                    prevRelation=attributes['fieldpath'], dosort=dosort,
                    pyresolver=pyresolver, relationStack=relationStack,
                    **kwargs,
                )

        def resultAppend(result, label, attributes, omit):
            if not self.db.application.allowedByPreference(**attributes):
                return
            if 'one_relation' in attributes or 'many_relation' in attributes:
                if not self.db.application.allowedByPreference(
                    **self.db.model.column(
                        attributes['one_relation'],
                    ).table.attributes,
                ):
                    return
                if not self.db.application.allowedByPreference(
                    **self.db.model.column(
                        attributes['many_relation'],
                    ).table.attributes,
                ):
                    return
            elif not attributes.get('virtual_column'):
                reltable = self.column(label).relatedTable()
                if reltable:
                    if not self.db.application.allowedByPreference(
                        **reltable.attributes,
                    ):
                        return
            gr = attributes.get('group') or ' '
            if '%' in gr:
                subgroups = dictExtract(attributes, 'subgroup_')
                gr = gr % subgroups
                attributes['group'] = gr
            grin = gr[0]
            if grin == '*' or grin == '_':
                attributes['group'] = gr[1:]
            if grin not in omit:
                result.setItem(label, xvalue(attributes), attributes)

        def convertAttributes(result, relnode, prevRelation, omit,
                              relationStack):
            attributes = dict(relnode.getAttr())
            attributes['fieldpath'] = gnrstring.concat(
                prevRelation, relnode.label,
            )
            if 'joiner' in attributes:
                joiner = attributes.pop('joiner')
                attributes.update(joiner)
                attributes['name_long'] = self.relationName(relnode.label)
                if attributes['mode'] == 'M':
                    attributes['group'] = (
                        attributes.get('many_group') or 'zz'
                    )
                    attributes['dtype'] = 'RM'
                    relkey = (
                        '%(one_relation)s/%(many_relation)s' % attributes
                    )
                else:
                    attributes['group'] = attributes.get('one_group')
                    attributes['dtype'] = 'RO'
                    fkeyattr = dict(relnode.attr)
                    fkeyattr.pop('joiner')
                    attributes['fkey'] = fkeyattr
                    relkey = (
                        '%(many_relation)s/%(one_relation)s' % attributes
                    )
                relkey = str(hash(relkey) & 0xffffffff)
                if relkey in relationStack.split('|'):
                    return
                attributes['relationStack'] = gnrstring.concat(
                    relationStack, relkey, '|',
                )
            else:
                if checkPermissions:
                    attributes.update(
                        self.model.getColPermissions(
                            relnode.label, **checkPermissions,
                        ),
                    )
                attributes['name_long'] = (
                    attributes.get('name_long') or relnode.label
                )
            return attributes

        tblmodel = self.model
        result = Bag()
        for relnode in tblmodel.relations:
            attributes = convertAttributes(
                result, relnode, prevRelation, omit, relationStack,
            )
            if attributes:
                if not attributes.get('user_forbidden'):
                    resultAppend(result, relnode.label, attributes, omit)
        for vcolname, vcol in list(tblmodel.virtual_columns.items()):
            targetcol = self.column(vcolname)  # noqa: F841
            attributes = dict(targetcol.attributes)  # REVIEW: dead code — immediately overwritten on next line
            attributes = dict()
            attributes.update(vcol.attributes)
            attributes['fieldpath'] = gnrstring.concat(
                prevRelation, vcolname,
            )
            attributes['name_long'] = (
                attributes.get('name_long') or vcolname
            )
            attributes['dtype'] = attributes.get('dtype') or 'T'
            resultAppend(result, vcolname, attributes, omit)

        for aliastbl in list(tblmodel.table_aliases.values()):
            relpath = tblmodel.resolveRelationPath(aliastbl.relation_path)
            attributes = dict(tblmodel.relations.getAttr(relpath))
            attributes['name_long'] = (
                aliastbl.attributes.get('name_long')
                or self.relationName(relpath)
            )
            attributes['group'] = aliastbl.attributes.get('group')
            attributes['fieldpath'] = gnrstring.concat(
                prevRelation, aliastbl.name,
            )
            joiner = attributes.pop('joiner')
            attributes.update(joiner)
            mode = attributes.get('mode')
            if mode == 'O':
                attributes['dtype'] = 'RO'
            elif mode == 'M':
                attributes['dtype'] = 'RM'
            resultAppend(result, aliastbl.name, attributes, omit)
        if dosort:
            result.sort(lambda a: a.getAttr('group', '').split('.'))
            grdict = dict([
                (k[6:], v)
                for k, v in list(self.attributes.items())
                if k.startswith('group_')
            ])
            if not grdict:
                return result
            newresult = Bag()
            for node in result:
                nodeattr = node.attr
                grplist = (nodeattr.get('group') or '').split('.')
                if grplist[-1] and grplist[-1].isdigit():
                    grplist.pop()
                if grplist and grplist[0] in grdict:
                    for j, kg in enumerate(grplist):
                        grplevel = '.'.join(grplist[0:j + 1])
                        if grplevel not in newresult:
                            newresult.setItem(
                                grplevel, None,
                                name_long=grdict.get(
                                    grplevel,
                                    grplevel.split('.')[-1],
                                ),
                            )
                    newresult.setItem(
                        '%s.%s' % ('.'.join(grplist), node.label),
                        node.getValue(),
                        node.getAttr(),
                    )
                else:
                    newresult.setItem(
                        node.label, node.getValue(), node.getAttr(),
                    )
            return newresult
        else:
            return result

    def setQueryCondition(self, condition_name, condition):
        """Set a named query condition in the current environment.

        :param condition_name: the condition identifier
        :param condition: the SQL condition string
        """
        self.db.currentEnv[
            'env_%s_condition_%s'
            % (self.fullname.replace('.', '_'), condition_name)
        ] = condition

    # ------------------------------------------------------------------
    #  Dynamic menu
    # ------------------------------------------------------------------

    def menu_dynamicMenuContent(self, columns=None, label_field=None,
                                title_field=None, **kwargs):
        """Fetch records for dynamic menu generation.

        :param columns: query columns
        :param label_field: field for menu item labels
        :param title_field: field for menu item titles
        """
        label_field = label_field or self.attributes.get('caption_field')
        columns = columns or '*'
        collist = columns.split(',')
        label_field = label_field or self.attributes.get('caption_field')
        if label_field and f'${label_field}' not in collist:
            collist.append(f'${label_field}')
        if title_field and f'${title_field}' not in collist:
            collist.append(f'${title_field}')
        return self.query(columns=','.join(collist), **kwargs).fetch()

    def menu_dynamicMenuLine(self, record, **kwargs):
        """Hook to customize a dynamic menu line.

        :param record: the record for this menu line
        :returns: dict of extra attributes
        """
        return {}

    # ------------------------------------------------------------------
    #  Totalizers
    # ------------------------------------------------------------------

    @property
    def totalizers(self):
        """Return the list of totalizer table names."""
        totalizers = dictExtract(self.attributes, 'totalizer_')
        return totalizers.values()

    def realignRelatedTotalizers(self):
        """Realign totalizers for all related totalizer tables."""
        for tbl in self.totalizers:
            self.db.table(tbl).totalize_realign_sql(empty=True)

    def updateTotalizers(self, record=None, old_record=None, evt=None,
                         _raw=None, _ignore_totalizer=None, **kwargs):
        """Update totalizer tables after a record change.

        :param record: the new record (``None`` on delete)
        :param old_record: the previous record
        :param evt: event type (``'D'`` for delete)
        :param _raw: if ``True``, this is a raw operation
        :param _ignore_totalizer: if ``True``, skip totalizer update
        """
        if _raw and _ignore_totalizer:
            return
        deferredTotalize = self.db.currentEnv.get('deferredTotalize')
        if deferredTotalize and self.fullname in deferredTotalize:
            return
        if evt == 'D':
            old_record = record
            record = None
        for tbl in self.totalizers:
            self.db.table(tbl).tt_totalize(
                record=record, old_record=old_record,
            )

    # ------------------------------------------------------------------
    #  Retention policy
    # ------------------------------------------------------------------

    @property
    @functools.lru_cache  # REVIEW: lru_cache on property — works but caches the descriptor, not per-instance
    def defaultRetentionPolicy(self):
        """Return the data retention policy defined on the table.

        Expects ``retention_policy`` attribute to be a 2-element list
        ``[filter_column, days]``.  Returns ``None`` if not configured.
        """
        table_policy = self.attributes.get("retention_policy", [])
        if not table_policy:
            return None
        if not isinstance(table_policy, (tuple, list)) or len(table_policy) != 2:
            logger.error(
                "Retention policy for %s must be a 2 element list/tuple",
                self.name,
            )
            return None
        if not isinstance(table_policy[1], int) or table_policy[1] < 1:
            logger.error(
                "Retention policy value for %s must be at least 1 day",
                self.name,
            )
            return None

        extra_where_filter = getattr(
            self, 'retention_extra_where', lambda: None,
        )()
        policy = dict(
            filter_column=table_policy[0],
            extra_where_filter=extra_where_filter,
            retention_period_default=table_policy[1],
            retention_period=table_policy[1],
        )
        return policy

    def executeRetentionPolicy(self, policy=None, dry_run=True):
        """Execute the retention policy deletion.

        :param policy: policy dict (from ``defaultRetentionPolicy``)
        :param dry_run: if ``True``, only return count without deleting
        :returns: summary dict with ``found_records`` and optionally
            ``deleted_records``
        """
        if not policy:
            return {}
        where_clause = f'${policy["filter_column"]} < :cutoff'
        extra_where_filter = policy.get("extra_where_filter", None)
        if extra_where_filter:
            where_clause = f'{where_clause} AND {extra_where_filter}'
        cutoff = datetime.now() - timedelta(days=policy['retention_period'])
        count = self.query(where=where_clause, cutoff=cutoff).count()
        summary = {"found_records": count}
        if dry_run:
            return summary
        else:
            r = self.deleteSelection(where=where_clause, cutoff=cutoff)
            summary['deleted_records'] = len(r)
            self.db.commit()
            return summary

    # ------------------------------------------------------------------
    #  DB implementation
    # ------------------------------------------------------------------

    @property
    def dbImplementation(self):
        """Return the DB implementation for the package's storename."""
        packageStorename = self.pkg.attributes.get('storename')
        if packageStorename:
            return self.db.dbstores[packageStorename].get('implementation')
