# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqltable.record : Record construction, retrieval and caching
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

"""Record construction, retrieval, caching and caption utilities.

Provides :class:`RecordMixin` — a mixin for :class:`~gnrsqltable.table.SqlTable`
that handles record building, default values, caching, unification,
caption rendering and related lookups.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from gnr.core import gnrstring
from gnr.core.gnrbag import Bag
from gnr.sql._typing import SqlTableBaseMixin
from gnr.sql.gnrsqldata import SqlRecord


class RecordMixin(SqlTableBaseMixin):
    """Record construction, retrieval, caching and captions."""

    # ------------------------------------------------------------------
    #  Type coercion
    # ------------------------------------------------------------------

    def recordCoerceTypes(self, record, null='NULL'):
        """Check and coerce types in *record*.

        :param record: dict-like object with colname→value pairs
        :param null: value treated as SQL NULL
        """
        converter = self.db.typeConverter
        _coerce_errors = []
        for k in record.keys():
            if not k.startswith('@'):
                if self.column(k) is None:
                    continue
                colattr = self.column(k).attributes
                dtype = self.column(k).dtype
                v = record[k]
                if (v is None) or (v == null) or v == '':
                    record[k] = None
                elif dtype in ['T', 'A', 'C'] and not isinstance(v, str):
                    if isinstance(v, bytes):
                        v = v.decode()
                    record[k] = str(v if not isinstance(v, float) else int(v))
                elif dtype == 'B' and not isinstance(v, str):
                    record[k] = bool(v)
                elif dtype == 'O' and isinstance(v, bytes):
                    record[k] = v
                else:
                    if dtype and isinstance(v, str):
                        if dtype not in ['T', 'A', 'C', 'X']:
                            v = converter.fromText(record[k], dtype)
                            if isinstance(v, tuple):
                                v = v[0]
                    if 'rjust' in colattr:
                        v = v.rjust(int(colattr['size']), colattr['rjust'])
                    elif 'ljust' in colattr:
                        v = v.ljust(int(colattr['size']), colattr['ljust'])
                    record[k] = v
                if isinstance(record[k], str):
                    record[k] = record[k].strip()
                    record[k] = record[k] or None  # avoid empty string
                    size = colattr.get('size')
                    if size:
                        sizelist = colattr['size'].split(':')
                        max_size = int(
                            sizelist[1] if len(sizelist) > 1 else sizelist[0],
                        )
                        if record[k] and len(record[k]) > max_size:
                            _coerce_errors.append(
                                f'Max len exceeded for field {k} '
                                f'{record[k]} ({max_size})',
                            )
                            record[k] = None
        if _coerce_errors:
            record['_coerce_errors'] = ','.join(_coerce_errors)

    # ------------------------------------------------------------------
    #  Record building
    # ------------------------------------------------------------------

    def buildrecord(self, fields, resolver_one: str = None, **kwargs):
        """Build a new record Bag from *fields*.

        :param fields: dict of field values
        :param resolver_one: resolver name for one-relations
        """
        newrecord = Bag()
        for fld_node in self.model.relations:
            fld = fld_node.label
            if not fld.startswith('@'):
                v = fields.get(fld)
                info = dict(self.columns[fld].attributes)
                dtype = info.get('dtype')
                if dtype == 'X':
                    try:
                        v = Bag(v)
                    except Exception:  # REVIEW: bare except — silently ignores Bag parse errors
                        pass
                newrecord.setItem(fld, v, info)
            elif resolver_one:
                if resolver_one is True:
                    continue
                info = dict(fld_node.getAttr())
                joiner = info.pop('joiner', None)
                if not joiner or joiner['mode'] == 'M':
                    continue
                info.pop('many_relation', None)
                info['_from_fld'] = joiner['many_relation']
                info['_target_fld'] = joiner['one_relation']
                info['mode'] = joiner['mode']
                v = None
                info['_resolver_name'] = resolver_one
                newrecord.setItem(fld, v, info)
        return newrecord

    def recordCopy(self, fromRecord, asBag=False):
        """Return a copy of *fromRecord*, excluding unique/system fields."""
        result = Bag() if asBag else dict()
        for colname, obj in self.model.columns.items():
            fieldMode = obj.attributes.get('fieldMode')
            if fieldMode not in (None, 'D'):
                continue
            if (obj.attributes.get('ignoreOnCopy')
                    or obj.attributes.get('onCopy') == 'ignore'):
                continue
            if obj.attributes.get('unique'):
                continue
            if (obj.attributes.get('_sysfield')
                    and colname not in (self.draftField, 'parent_id')):
                continue
            val = fromRecord.get(colname)
            if val is not None:
                result[colname] = val
        return result

    def newrecord(self, assignId=False, resolver_one=None,
                  _fromRecord=None, **kwargs):
        """Create a new record with default values.

        :param assignId: if ``True``, assign a new primary key
        :param resolver_one: resolver name for one-relations
        :param _fromRecord: optional record to copy values from
        """
        defaultValues = self.defaultValues() or {}
        if _fromRecord:
            defaultValues.update(self.recordCopy(_fromRecord))
        defaultValues.update(kwargs)
        newrecord = self.buildrecord(defaultValues, resolver_one=resolver_one)
        if assignId:
            newrecord[self.pkey] = self.newPkeyValue(record=newrecord)
        self.extendDefaultValues(newrecord)
        return newrecord

    # ------------------------------------------------------------------
    #  Record caching
    # ------------------------------------------------------------------

    def cachedRecord(self, pkey=None, virtual_columns=None, keyField=None,
                     createCb=None, cacheInPage=None):
        keyField = keyField or self.pkey
        ignoreMissing = createCb is not None

        def recordFromCache(cache=None, pkey=None,
                            virtual_columns_set=None):
            cacheNode = cache.getNode(pkey)
            if cacheNode:
                result = cacheNode.value
                cached_virtual_columns_set = cacheNode.getAttr(
                    'virtual_columns_set',
                )
            else:
                result, cached_virtual_columns_set = None, None
            in_cache = bool(result)
            if (in_cache
                    and not virtual_columns_set.issubset(
                        cached_virtual_columns_set)):
                in_cache = False
                virtual_columns_set = virtual_columns_set.union(
                    cached_virtual_columns_set,
                )
            if not in_cache:
                result = self.record(
                    virtual_columns=','.join(virtual_columns_set),
                    ignoreMissing=ignoreMissing,
                    **{keyField: pkey},
                ).output('dict')
                if (not result) and createCb:
                    result = createCb(pkey) or result
                    if virtual_columns and result:
                        result = self.record(
                            virtual_columns=','.join(virtual_columns_set),
                            **{keyField: pkey},
                        ).output('dict')
                cache.setItem(
                    pkey, result,
                    virtual_columns_set=virtual_columns_set,
                )
            return dict(result), in_cache

        virtual_columns_set = (
            set(virtual_columns.split(',')) if virtual_columns else set()
        )
        return self.tableCachedData(
            'cachedRecord', recordFromCache, pkey=pkey,
            virtual_columns_set=virtual_columns_set,
            cacheInPage=cacheInPage,
        )

    def cachedKey(self, topic):
        if self.multidb == '*' or not self.use_dbstores() is False:
            storename = self.db.rootstore
        else:
            storename = self.db.currentStorename
        return '%s.%s.%s' % (storename, topic, self.fullname)

    def tableCachedData(self, topic, cb, cacheInPage=None, **kwargs):
        currentPage = self.db.currentPage
        cacheKey = self.cachedKey(topic)
        if currentPage:
            cacheInPage = (
                self.db.currentEnv.get('cacheInPage')
                if cacheInPage is None else cacheInPage
            )
            if cacheInPage:
                store = getattr(currentPage, '_pageTableCache', None)
                if not store:
                    currentPage._pageTableCache = {}
                    store = currentPage._pageTableCache
                localcache = store.get(cacheKey) or Bag()
            else:
                store = currentPage.pageStore()
                localcache = store.getItem(cacheKey)
                localcache = localcache or Bag()
            data, in_cache = cb(cache=localcache, **kwargs)
            if store is not None and not in_cache:
                if cacheInPage:
                    store[cacheKey] = localcache
                else:
                    with currentPage.pageStore() as store:
                        store.setItem(
                            cacheKey, localcache,
                            _caching_table=self.fullname,
                        )
        else:
            localcache = self.db.currentEnv.setdefault(cacheKey, Bag())
            data, in_cache = cb(cache=localcache, **kwargs)
        return data

    def guessPkey(self, identifier, tolerant=False):
        if identifier is None:
            return
        def cb(cache=None, identifier=None, **kwargs):
            if identifier in cache:
                return cache[identifier], True
            codeField = None
            result = None
            if ':' in identifier:
                wherelist = []
                wherekwargs = dict()

                for cond in identifier.split(','):
                    cond = cond.strip()
                    codeField, codeVal = cond.split(':')
                    if codeVal is None or codeVal == '':
                        continue
                    cf = '${}'.format(codeField) if not (codeField.startswith('$') or codeField.startswith('@')) else codeField
                    vf = codeField.replace('@', '_').replace('.', '_').replace('$', '')
                    wherelist.append('%s ILIKE :v_%s' % (cf, vf) if tolerant else '%s = :v_%s' % (cf, vf))
                    wherekwargs['v_%s' % vf] = codeVal
                result = self.readColumns(columns='$%s' % self.pkey, where=' AND '.join(wherelist),
                                        subtable='*', **wherekwargs)
            elif hasattr(self, 'sysRecord_%s' % identifier):
                result = self.sysRecord(identifier)[self.pkey]
            elif self.pkey != 'id' or not codeField:
                result = identifier
            cache[identifier] = result
            return result, False
        return self.tableCachedData('guessedPkey', cb, identifier=identifier)

    # ------------------------------------------------------------------
    #  Record retrieval
    # ------------------------------------------------------------------

    def record(self, pkey=None, where=None,
               lazy=None, eager=None, mode=None, relationDict=None,
               ignoreMissing=False, virtual_columns=None,
               ignoreDuplicate=False, bagFields=True,
               joinConditions=None, sqlContextName=None,
               for_update=False, _storename=None,
               checkPermissions=False, aliasPrefix=None, **kwargs):
        """Retrieve a single record as a :class:`~gnr.sql.gnrsqldata.SqlRecord`.

        :param pkey: primary key value
        :param where: WHERE clause
        :param mode: output mode (``'bag'``, ``'dict'``, ``'json'``)
        :param ignoreMissing: if ``True``, return empty on missing record
        :param for_update: lock the row
        """
        packageStorename = self.pkg.attributes.get('storename')
        if packageStorename and _storename is None:
            _storename = packageStorename
        record = SqlRecord(
            self, pkey=pkey, where=where,
            lazy=lazy, eager=eager,
            relationDict=relationDict,
            ignoreMissing=ignoreMissing,
            virtual_columns=virtual_columns,
            ignoreDuplicate=ignoreDuplicate,
            joinConditions=joinConditions,
            sqlContextName=sqlContextName,
            bagFields=bagFields, for_update=for_update,
            _storename=_storename,
            checkPermissions=checkPermissions,
            aliasPrefix=aliasPrefix, **kwargs,
        )
        if mode:
            return record.output(mode)
        else:
            return record

    def recordAs(self, record, mode='bag', virtual_columns=None,
                 ignoreMissing=True):
        """Coerce *record* (bag, dict or pkey string) to the requested *mode*.

        :param record: a bag, dict or primary key string
        :param mode: ``'dict'``, ``'bag'`` or ``'pkey'``
        """
        if not hasattr(record, 'items'):
            if mode == 'pkey':
                return record
            else:
                return self.record(
                    pkey=record, mode=mode,
                    virtual_columns=virtual_columns,
                    ignoreMissing=ignoreMissing,
                )
        if mode == 'pkey':
            return record.get('pkey', None) or record.get(self.pkey)
        if mode == 'dict' and not isinstance(record, dict):
            return dict([
                (k, v) for k, v in list(record.items())
                if not k.startswith('@')
            ])
        if mode == 'bag' and (virtual_columns or not isinstance(record, Bag)):
            pkey = record.get('pkey', None) or record.get(self.pkey)
            if pkey:
                record = self.record(
                    pkey=pkey, mode=mode,
                    virtual_columns=virtual_columns,
                )
        return record

    # ------------------------------------------------------------------
    #  Unification
    # ------------------------------------------------------------------

    def restoreUnifiedRecord(self, record=None):
        r = Bag(record['__moved_related'])  # REVIEW: assumes record has '__moved_related' key
        if not r:
            return
        relations = r.getItem('relations')
        if hasattr(self, 'onRestoring'):
            self.onRestoring(record=record)
        if relations:
            for n in relations:
                tblobj = self.db.table(n.attr['tblname'])
                updater = dict()
                updater[n.attr['fkey']] = record['id']  # REVIEW: hardcodes 'id' — should use self.pkey
                if n.value:
                    tblobj.batchUpdate(updater, _pkeys=n.value.split(','))
        record['__moved_related'] = None

    def _onUnifying(self, destRecord=None, sourceRecord=None,
                    moved_relations=None, relations=None):
        pass

    def unifyRelatedRecords(self, sourceRecord=None, destRecord=None,
                            moved_relations=None, relations=None):
        relations = list(self.model.relations.keys())
        old_destRecord = dict(destRecord)
        upd_destRec = False
        for k in relations:
            n = self.relations.getNode(k)
            joiner = n.attr.get('joiner')
            if joiner and joiner['mode'] == 'M':
                if joiner.get('external_relation'):
                    continue
                fldlist = joiner['many_relation'].split('.')
                tblname = '.'.join(fldlist[0:2])
                tblobj = self.db.table(tblname)
                fkey = fldlist[-1]
                joinkey = joiner['one_relation'].split('.')[-1]
                updater = dict()
                if not destRecord[joinkey]:
                    destRecord[joinkey] = sourceRecord[joinkey]
                    upd_destRec = True
                updater[fkey] = destRecord[joinkey]
                updatedpkeys = tblobj.batchUpdate(
                    updater,
                    where='$%s=:spkey' % fkey,
                    spkey=sourceRecord[joinkey],
                    _raw_update=True,
                )
                moved_relations.setItem(
                    'relations.%s' % tblname.replace('.', '_'),
                    ','.join([str(pk) for pk in updatedpkeys]),
                    tblname=tblname, fkey=fkey,
                )
        if upd_destRec:
            self.raw_update(destRecord, old_destRecord)
        return moved_relations

    def unifyRecords(self, sourcePkey=None, destPkey=None):
        sourceRecord = self.record(
            pkey=sourcePkey, for_update=True,
        ).output('dict')
        destRecord = self.record(
            pkey=destPkey, for_update=True,
        ).output('dict')
        self._unifyRecords_default(sourceRecord, destRecord)

    def _unifyRecords_default(self, sourceRecord=None, destRecord=None):
        moved_relations = Bag()
        with self.db.tempEnv(unifying='related'):
            self._onUnifying(
                sourceRecord=sourceRecord, destRecord=destRecord,
                moved_relations=moved_relations,
            )
            if hasattr(self, 'onUnifying'):
                self.onUnifying(
                    sourceRecord=sourceRecord, destRecord=destRecord,
                    moved_relations=moved_relations,
                )
            moved_relations = self.unifyRelatedRecords(
                sourceRecord=sourceRecord, destRecord=destRecord,
                moved_relations=moved_relations,
            )
        with self.db.tempEnv(unifying='main_record'):
            if self.model.column('__moved_related') is not None:
                old_record = dict(sourceRecord)
                moved_relations.setItem(
                    'destPkey', sourceRecord[self.pkey],
                )
                moved_relations = moved_relations.toXml()
                sourceRecord.update(
                    __del_ts=datetime.now(),
                    __moved_related=moved_relations,
                )
                self.raw_update(sourceRecord, old_record=old_record)
            else:
                self.delete(sourceRecord[self.pkey])

    # ------------------------------------------------------------------
    #  Relation checks
    # ------------------------------------------------------------------

    def hasRelations(self, recordOrPkey):
        return bool(self.currentRelations(recordOrPkey, checkOnly=True))

    def currentRelations(self, recordOrPkey, checkOnly=False):
        result = Bag()
        i = 0
        if isinstance(recordOrPkey, str):
            record = self.record(pkey=recordOrPkey).output('dict')
        else:
            record = recordOrPkey
        for n in self.model.relations:
            joiner = n.attr.get('joiner')
            if joiner and joiner['mode'] == 'M':
                rowdata = Bag()
                fldlist = joiner['many_relation'].split('.')
                tblname = fldlist[0:2]
                linktblobj = self.db.table('.'.join(tblname))
                fkey = fldlist[-1]
                joinkey = joiner['one_relation'].split('.')[-1]
                rel_count = linktblobj.query(
                    where='$%s=:spkey' % fkey,
                    spkey=record[joinkey],
                ).count()
                linktblobj_name = linktblobj.fullname
                rowdata.setItem('linktbl', linktblobj_name)
                rowdata.setItem('count', rel_count)
                if rel_count:
                    if checkOnly:
                        return True
                    result.setItem('r_%i' % i, rowdata)
                i += 1
        return result

    # ------------------------------------------------------------------
    #  Duplicates
    # ------------------------------------------------------------------

    def findDuplicates(self, allrecords=True):
        dup_records = self.query(
            where=(
                "($_duplicate_finder IS NOT NULL) "
                "AND ($_duplicate_finder!='')"
            ),
            columns='$_duplicate_finder,count(*)',
            having='count(*)>1',
            group_by='$_duplicate_finder',
        ).fetch()
        duplicated = [r[0] for r in dup_records]
        if not duplicated:
            return []
        q = self.query(
            where='$_duplicate_finder IN :dpf', dpf=duplicated,
            columns='$_duplicate_finder',
            order_by='$_duplicate_finder,$__mod_ts desc',
        )
        return [r['pkey'] for r in q.fetch()]

    # ------------------------------------------------------------------
    #  Default values
    # ------------------------------------------------------------------

    def extendDefaultValues(self, newrecord=None):
        fkeysColsToRead = defaultdict(dict)
        for colname, colobj in self.columns.items():
            defaultFrom = colobj.attributes.get('defaultFrom')
            dtype = colobj.attributes.get('dtype')
            if not defaultFrom:
                continue
            newrec_value = newrecord.get(colname)
            if newrec_value is not None:
                if isinstance(newrec_value, Bag):
                    if len(newrec_value) > 0:
                        continue
                else:
                    continue
            pathlist = defaultFrom.split('.')
            if pathlist[-1].startswith('@'):
                pathlist.append(colname)
            fromFkey = pathlist[0][1:]
            colToRead = '.'.join(pathlist[1:])
            fromKeyValue = newrecord.get(fromFkey)
            if fromKeyValue is None:
                continue
            colToRead = (
                colToRead if colToRead.startswith('@') else f'${colToRead}'
            )
            fkeysColsToRead[(fromFkey, fromKeyValue)][colname] = colToRead
        if not fkeysColsToRead:
            return
        currEnv = self.db.currentEnv
        for identifier, coldict in fkeysColsToRead.items():
            cacheIdentifier = (
                f'{self.fullname.replace(".", "_")}'
                f'_extendedDefaults_{identifier}'
            )
            cachedDefaults = currEnv.get(cacheIdentifier)
            if not cachedDefaults:
                fkey, fkeyValue = identifier
                columns = ','.join([
                    f"{colToRead} AS {colname}"
                    for colname, colToRead in coldict.items()
                ])
                relatedTblobj = self.column(fkey).relatedTable().dbtable
                f = relatedTblobj.query(
                    where=f'${relatedTblobj.pkey}=:fkeyValue',
                    fkeyValue=fkeyValue, columns=columns,
                    addPkeyColumn=False, limit=1,
                    excludeDraft=False, ignorePartition=True,
                    excludeLogicalDeleted=False, subtable='*',
                ).fetch()
                cachedDefaults = dict()
                for k, v in f[0].items():  # REVIEW: f[0] — no check if fetch returned empty results
                    if self.column(k).getAttr('dtype') == 'X':
                        v = Bag(v)
                    cachedDefaults[k] = v
                currEnv[cacheIdentifier] = cachedDefaults
            newrecord.update(cachedDefaults)

    def defaultValues(self):
        """Return a dict of column defaults from model attributes."""
        return {
            colobj.name: colobj.attributes['default']
            for colobj in self.columns.values()
            if 'default' in colobj.attributes
        }

    def sampleValues(self):
        """Return a dict of sample values from model attributes."""
        return dict([
            (x.name, x.attributes['sample'])
            for x in list(self.columns.values())
            if 'sample' in x.attributes
        ])

    # ------------------------------------------------------------------
    #  Pkey checking
    # ------------------------------------------------------------------

    def checkPkey(self, record):
        """Ensure *record* has a primary key, generating one if needed.

        :returns: ``True`` if a new key was assigned
        """
        pkeyValue = record.get(self.pkey)
        newkey = False
        if pkeyValue in (None, ''):
            newkey = True
            pkeyValue = self.newPkeyValue(record=record)
            if pkeyValue is not None:
                record[self.pkey] = pkeyValue
        return newkey

    # ------------------------------------------------------------------
    #  Caption rendering
    # ------------------------------------------------------------------

    def rowcaptionDecode(self, rowcaption=None):
        """Decode a rowcaption template into (fields, mask).

        :param rowcaption: template string (e.g. ``'$name,$code:%s - %s'``)
        """
        rowcaption = rowcaption or self.rowcaption
        if not rowcaption:
            return [], ''
        if ':' in rowcaption:
            fields, mask = rowcaption.split(':', 1)
        else:
            fields, mask = rowcaption, None
        fields = fields.replace('*', self.pkey)
        fields = self.columnsFromString(fields)
        if not mask:
            mask = ' - '.join(['%s' for k in fields])
        return fields, mask

    def newRecordCaption(self, record=None):
        return self.newrecord_caption

    def recordCaption(self, record, newrecord=False, rowcaption=None):
        """Render the human-readable caption for *record*.

        :param record: dict or Bag
        :param newrecord: if ``True``, return the new-record caption
        :param rowcaption: override template
        """
        if newrecord:
            return self.newRecordCaption(record)
        else:
            fields, mask = self.rowcaptionDecode(rowcaption)
            if not fields:
                return ''
            fields = [f.lstrip('$') for f in fields]
            if not isinstance(record, Bag):
                fields = [self.db.colToAs(f) for f in fields]
            tblname = self.name
            cols = [
                (c, gnrstring.toText(
                    record.get(c, tblname), locale=self.db.locale,
                ))
                for c in fields
            ]
            if '$' in mask:
                caption = gnrstring.templateReplace(mask, dict(cols))
            else:
                caption = mask % tuple([v for k, v in cols])
            return caption
