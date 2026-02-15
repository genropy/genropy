#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy sql - see LICENSE for details
# module gnrsqldata_selection : SQL selection result wrapper
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU.
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import shutil
import pickle
import itertools
import tempfile
from xml.sax import saxutils

from gnr.core.gnrdecorator import deprecated
from gnr.core.gnrlang import uniquify, MinValue
from gnr.core.gnrlist import GnrNamedList
from gnr.core import gnrclasses
from gnr.core import gnrstring
from gnr.core import gnrlist
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.core.gnrbag import Bag, BagAsXml
from gnr.core.gnranalyzingbag import AnalyzingBag
from gnr.sql.gnrsql_exceptions import GnrSqlException, SelectionExecutionError
from gnr.sql.gnrsqldata_record import SqlRelatedRecordResolver


class SqlSelection(object):
    """It is the resulting data from the execution of an istance of the :class:`SqlQuery`. Through the
    SqlSelection you can get data into differents modes: you can use the :meth:`output()` method or you
    can :meth:`freeze()` it into a file. You can also use the :meth:`sort()` and the :meth:`filter()` methods
    on a SqlSelection."""
    def __init__(self, dbtable, data, index=None, colAttrs=None, key=None, sortedBy=None,
                 joinConditions=None, sqlContextName=None, explodingColumns=None, checkPermissions=None,
                 querypars=None,_aggregateRows=False,_aggregateDict=None):
        self._frz_data = None
        self._frz_filtered_data = None
        self.dbtable = dbtable
        self.querypars = querypars
        self.tablename = dbtable.fullname
        self.colAttrs = colAttrs or {}
        self.explodingColumns = explodingColumns
        self.aggregateDict = _aggregateDict
        if _aggregateRows == True:
            data = self._aggregateRows(data, index, explodingColumns,aggregateDict=_aggregateDict)
        self._data = data
        if key:
            self.setKey(key)
        elif 'pkey' in index:
            self.key = 'pkey'
        else:
            self.key = None
        self.sortedBy = sortedBy
        if sortedBy:
            self.sort(sortedBy)
        self._keyDict = None
        self._filtered_data = None
        self._index = index
        self.columns = self.allColumns
        self.freezepath = None
        self.analyzeBag = None
        self.isChangedSelection = True
        self.isChangedData = True
        self.isChangedFiltered = True
        self.joinConditions = joinConditions
        self.sqlContextName = sqlContextName
        self.checkPermissions = checkPermissions

    def _aggregateRows(self, data, index, explodingColumns,aggregateDict=None):
        if self.explodingColumns:
            newdata = []
            datadict = {}
            mixColumns = [c for c in explodingColumns if c in index and not self.colAttrs[c].get('one_one') and not( aggregateDict and (c in aggregateDict))]
            for d in data:
                if not d['pkey'] in datadict:
                    for col in mixColumns:
                        d[col] = [d[col]]
                    if aggregateDict:
                        for k,v in list(aggregateDict.items()):
                            subfld = v[0]
                            d[subfld] = d.get(subfld) or {}
                            sr = d[subfld].setdefault(d[v[2]],{})
                            sr[v[1]] = d[k]
                    newdata.append(d)
                    datadict[d['pkey']] = d
                else:
                    masterRow = datadict[d['pkey']]
                    for col in mixColumns:
                        if d[col] not in masterRow[col]:
                            masterRow[col].append(d[col])
                            # masterRow[col].sort()
                            masterRow[col].sort(key=lambda x: MinValue if x is None else x)
                    if aggregateDict:
                        for k,v in list(aggregateDict.items()):
                            subfld = v[0]
                            sr = masterRow[subfld].setdefault(d[v[2]],{})
                            sr[v[1]] = d[k]
            data = newdata
            for d in data:
                for col in mixColumns:
                    d[col] = self.dbtable.fieldAggregate(col,d[col],fieldattr= self.colAttrs[col],onSelection=True)
        return data

    def setKey(self, key):
        """Internal method. Set the data of a SqlQuery in a dict

        :param key: the key.
        """
        self.key = key
        for i, r in enumerate(self._data):
            r[key] = i
        if key not in self._index:
            self._index[key] = len(self._index)

    def _get_allColumns(self):
        items = list(self._index.items())
        result = [None] * len(items)
        for k, v in items:
            result[v] = k
        return result

    allColumns = property(_get_allColumns)

    def _get_db(self):
        return self.dbtable.db

    db = property(_get_db)

    def _get_keyDict(self):
        if not self._keyDict:
            self._keyDict = dict([(r[self.key], r) for r in self.data])
        return self._keyDict

    keyDict = property(_get_keyDict)

    def output(self, mode, columns=None, offset=0, limit=None,
               filterCb=None, subtotal_rows=None, formats=None, locale=None, dfltFormats=None,
               asIterator=False, asText=False, **kwargs):
        """Return the selection into differents format

        :param mode: There are different options you can set:

                     * `mode='pkeylist'`: TODO
                     * `mode='records'`: TODO
                     * `mode='data'`: TODO
                     * `mode='tabtext'`: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param offset: the same of the sql "OFFSET"
        :param limit: number of result's rows. Corresponding to the sql "LIMIT" operator. For more
                      information, check the :ref:`sql_limit` section
        :param filterCb: TODO
        :param subtotal_rows: TODO
        :param formats: TODO
        :param locale: the current locale (e.g: en, en_us, it)
        :param dfltFormats: TODO
        :param asIterator: boolean. TODO
        :param asText: boolean. TODO"""
        if subtotal_rows :
            subtotalNode = self.analyzeBag.getNode(subtotal_rows) if self.analyzeBag else None
            if subtotalNode and subtotalNode.attr:
                filterCb = lambda r: r[self.key] in subtotalNode.attr['idx']
        if mode == 'pkeylist' or mode == 'records':
            columns = 'pkey'
        if isinstance(columns, str):
            columns = gnrstring.splitAndStrip(columns, ',')
        if not columns:
            columns = self.allColumns
            if self.aggregateDict:
                columns = [c for c in columns if c not in self.aggregateDict]
        self.columns = columns
        if mode == 'data':
            columns = ['**rawdata**']

        if asIterator:
            prefix = 'iter'
        else:
            prefix = 'out'

        if mode == 'tabtext':
            asText = True
        if asText and not formats:
            formats = dict([(k, self.colAttrs.get(k, dict()).get('format')) for k in self.columns])

        outmethod = '%s_%s' % (prefix, mode)
        if hasattr(self, outmethod):
            outgen = self._out(columns=columns, offset=offset, limit=limit, filterCb=filterCb)
            if formats:
                outgen = self.toTextGen(outgen, formats=formats, locale=locale, dfltFormats=dfltFormats or {})
            return getattr(self, outmethod)(outgen, **kwargs) #calls the output method
        else:
            raise SelectionExecutionError('Not existing mode: %s' % outmethod)

    def __len__(self):
        return len(self.data)

    def _get_data(self):
        if self._filtered_data is not None:
            return self._filtered_data
        else:
            return self._data

    data = property(_get_data)

    def _get_filtered_data(self):
        if self._frz_filtered_data == 'frozen':
            self._freeze_filtered('r')
        return self._frz_filtered_data

    def _set_filtered_data(self, value):
        self._frz_filtered_data = value

    _filtered_data = property(_get_filtered_data, _set_filtered_data)

    def _get_full_data(self):
        if self._frz_data == 'frozen':
            self._freeze_data('r')
        return self._frz_data

    def _set_full_data(self, value):
        self._frz_data = value

    _data = property(_get_full_data, _set_full_data)

    def _freezeme(self):
        if self.analyzeBag != None:
            self.analyzeBag.makePicklable()
        saved = self.dbtable, self._data, self._filtered_data
        self.dbtable, self._data, self._filtered_data = None, 'frozen', 'frozen' * bool(self._filtered_data) or None
        selection_path = '%s.pik' % self.freezepath
        dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection',suffix='.pik')
        with os.fdopen(dumpfile_handle, "wb") as f:
            pickle.dump(self, f)
        shutil.move(dumpfile_path, selection_path)
        self.dbtable, self._data, self._filtered_data = saved

    def _freeze_data(self, readwrite):
        pik_path = '%s_data.pik' % self.freezepath
        if readwrite == 'w':
            dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_data',suffix='.pik')
            with os.fdopen(dumpfile_handle, "wb") as f:
                pickle.dump(self._data, f)
            shutil.move(dumpfile_path, pik_path)
        else:
            with open(pik_path, 'rb') as f:
                self._data = pickle.load(f)

    def _freeze_pkeys(self, readwrite):
        if not self.dbtable.pkey:
            return
        pik_path = '%s_pkeys.pik' % self.freezepath
        if readwrite == 'w':
            dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_data',suffix='.pik')
            with os.fdopen(dumpfile_handle, "wb") as f:
                pickle.dump(self.output('pkeylist'), f)
            shutil.move(dumpfile_path, pik_path)
        else:
            with open(pik_path, 'rb') as f:
                return pickle.load(f)

    def _freeze_filtered(self, readwrite):
        fpath = '%s_filtered.pik' % self.freezepath
        if readwrite == 'w' and self._filtered_data is None:
            if os.path.isfile(fpath):
                os.remove(fpath)
        else:
            if readwrite == 'w':
                dumpfile_handle, dumpfile_path = tempfile.mkstemp(prefix='gnrselection_filtered',suffix='.pik')
                with os.fdopen(dumpfile_handle, "w") as f:
                    pickle.dump(self._filtered_data, f)
                shutil.move(dumpfile_path, fpath)
            else:
                with open(fpath, 'rb') as f:
                    self._filtered_data = pickle.load(f)

    def freeze(self, fpath, autocreate=False,freezePkeys=False):
        """TODO

        :param fpath: the freeze path
        :param autocreate: boolean. if ``True``, TODO"""
        self.freezepath = fpath
        self.isChangedSelection = False
        self.isChangedData = False
        self.isChangedFiltered = False
        if autocreate:
            dirname = os.path.dirname(fpath)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        self._freezeme()
        self._freeze_data('w')
        self._freeze_filtered('w')
        if freezePkeys:
            self._freeze_pkeys('w')

    def freezeUpdate(self):
        """TODO"""
        if self.isChangedData:
            self._freeze_data('w')
        if self.isChangedFiltered:
            self._freeze_filtered('w')

        isChangedSelection = self.isChangedSelection
        self.isChangedSelection = False # clear all changes flag before freeze self
        self.isChangedData = False
        self.isChangedFiltered = False
        if isChangedSelection:
            self._freezeme()

    def getByKey(self, k):
        """TODO

        :param k: TODO"""
        return self.keyDict[k]

    def sort(self, *args):
        """TODO"""
        args = list(args)
        args = [x.replace('.','_').replace('@','_') for x in args]
        if len(args) == 1 and (',' in args[0]):
            args = gnrstring.splitAndStrip(args[0], ',')
        if args != self.sortedBy:
            if self.explodingColumns:
                for k, arg in enumerate(args):
                    if arg.split(':')[0] in self.explodingColumns:
                        args[k] = arg.replace('*', '')
            self.sortedBy = args
            gnrlist.sortByItem(self.data, *args)
            if self.key == 'rowidx':
                self.setKey('rowidx')
            self.isChangedSelection = True #prova
            if not self._filtered_data:
                self.isChangedData = True
            else:
                self.isChangedFiltered = True


    def filter(self, filterCb=None):
        """TODO

        :param filterCb: TODO.
        """
        if filterCb:
            self._filtered_data = list(filter(filterCb, self._data))
        else:
            self._filtered_data = None
        self.isChangedFiltered = True

    def extend(self, selection, merge=True):
        """TODO

        :param selection: TODO
        :param merge: boolean. TODO
        """
        if not merge:
            if self._index != selection._index:
                raise GnrSqlException("Selections columns mismatch")
            else:
                l = [self.newRow(r) for r in selection.data]
        else:
            l = [self.newRow(r) for r in selection.data]
        self.data.extend(l)

    def apply(self, cb):
        """TODO

        :param cb: TODO
        """
        rowsToChange = []
        for i, r in enumerate(self._data):
            result = cb(r)
            if isinstance(result, dict):
                r.update(result)
            else:
                rowsToChange.append((i, result))

        if rowsToChange:
            rowsToChange.reverse()
            for i, change in rowsToChange:
                if change is None:
                    self._data.pop(i)
                else:
                    self._data.pop(i)
                    change.reverse()
                    for r in change:
                        self.insert(i, r)

        self.isChangedData = True

    def insert(self, i, values):
        """TODO

        :param i: TODO
        :param values: TODO
        """
        self._data.insert(i, self.newRow(values))

    def append(self, values):
        """TODO

        :param i: TODO
        :param values: TODO
        """
        self._data.append(self.newRow(values))

    def newRow(self, values):
        """Add a new row and return it

        :param values: TODO"""
        r = GnrNamedList(self._index)
        r.update(values)
        return r

    def remove(self, cb):
        """TODO

        :param cb: TODO"""
        self._data = list(filter(not(cb), self._data))
        self.isChangedData = True

    def totalize(self, group_by=None, sum=None, collect=None, distinct=None,
                 keep=None, key=None, captionCb=None, **kwargs):
        """TODO

        :param group_by: the sql "GROUP BY" clause. For more information check the :ref:`sql_group_by` section
        :param sum: TODO
        :param collect: TODO
        :param distinct: boolean, ``True`` for getting a "SELECT DISTINCT"
        :param keep: TODO
        :param key: TODO
        :param captionCb: TODO"""
        if group_by is None:
            self.analyzeBag = None
        else:
            self.analyzeBag = self.analyzeBag or AnalyzingBag()
            if key is None:
                key = self.key
            elif key == '#':
                key = None
            if group_by:
                group_by = [x.replace('@', '_').replace('.', '_').replace('$', '') if isinstance(x, str) else x
                            for x in group_by]
            if keep:
                keep = [x.replace('@', '_').replace('.', '_').replace('$', '') if isinstance(x, str) else x for x
                        in keep]
            self.analyzeKey = key
            self.analyzeBag.analyze(self, group_by=group_by, sum=sum, collect=collect,
                                    distinct=distinct, keep=keep, key=key, captionCb=captionCb, **kwargs)
        return self.analyzeBag

    @deprecated
    def analyze(self, group_by=None, sum=None, collect=None, distinct=None, keep=None, key=None, **kwargs):
        """.. warning:: deprecated since version 0.7"""
        self.totalize(group_by=group_by, sum=sum, collect=collect, distinct=distinct, keep=keep, key=key, **kwargs)

    def totalizer(self, path=None):
        """TODO

        :param path: TODO. """
        if path and self.analyzeBag:
            return self.analyzeBag[path]
        else:
            return self.analyzeBag

    def totalizerSort(self, path=None, pars=None):
        """TODO

        :param path: TODO.
        :param pars: TODO.
        """
        tbag = self.totalizer(path)
        if pars:
            tbag.sort(pars)
        else:
            tbag.sort()

    def totals(self, path=None, columns=None):
        """TODO

        :param path: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section. """
        if isinstance(columns, str):
            columns = gnrstring.splitAndStrip(columns, ',')

        tbag = self.totalizer(path)

        result = []
        for tnode in tbag:
            tattr = tnode.getAttr()
            result.append(dict([(k, tattr[k]) for k in columns]))

        return result


    def sum(self,columns=None):
        if isinstance(columns, str):
            columns = columns.split(',')
        result  = list()
        if not columns or not self.data:
            return result
        data = list(zip(*[[r[c] for c in columns] for r in self.data]))
        for k,c in enumerate(columns):
            result.append(sum([r for r in data[k] if r is not None]))
        return result


    def _out(self, columns=None, offset=0, limit=None, filterCb=None):
        if filterCb:
            source = filter(filterCb, self.data)
        else:
            source = self.data
        if limit:
            stop = offset + limit
        else:
            stop = None
        columns = [cname for cname in columns if not self.colAttrs.get(cname,{}).get('user_forbidden')]
        if columns != ['**rawdata**']:
            for r in itertools.islice(source, offset, stop):
                yield r.extractItems(columns)
        else:
            for r in itertools.islice(source, offset, stop):
                yield r

    def toTextGen(self, outgen, formats, locale, dfltFormats):
        """TODO

        :param outgen: TODO
        :param formats: TODO
        :param locale: the current locale (e.g: en, en_us, it)
        :param dfltFormats: TODO"""
        def _toText(cell):
            k, v = cell
            v = gnrstring.toText(v, format=formats.get(k) or dfltFormats.get(type(v)), locale=locale)
            return (k, v)

        for r in outgen:
            yield list(map(_toText, r))

    def __iter__(self):
        return self.data.__iter__()

    def out_listItems(self, outsource):
        """Return the outsource.

        :param outsource: TODO"""
        return outsource

    def out_count(self, outsource):
        """Return the number of rows in the outsource.

        :param outsource: TODO"""
        #dubbio secondo me non dovrebbe esserci
        n = 0
        for r in outsource:
            n += 1
        return n

    def out_distinctColumns(self, outsource):
        """TODO

        :param outsource: TODO"""
        return [uniquify(x) for x in zip(*[[v for k, v in r] for r in outsource])]

    def out_distinct(self, outsource):
        """TODO

        :param outsource: TODO"""
        return set([tuple([col[1] for col in r]) for r in outsource])

    def out_generator(self, outsource):
        """Return the outsource

        :param outsource: TODO"""
        return outsource

    def iter_data(self, outsource):
        """Return the outsource

        :param outsource: TODO"""
        return outsource

    def out_data(self, outsource):
        """Return a list of the outsource's rows.

        :param outsource: TODO"""
        return [r for r in outsource]

    def iter_dictlist(self, outsource):
        """A generator function that returns a dict of the outsource's rows.

        :param outsource: TODO"""
        for r in outsource:
            yield dict(r)

    def out_dictlist(self, outsource):
        """TODO

        :param outsource: TODO"""
        return [dict(r) for r in outsource]

    def out_json(self, outsource):
        """TODO

        :param outsource: TODO"""
        return gnrstring.toJson(self.out_dictlist(outsource))

    def out_list(self, outsource):
        """TODO

        :param outsource: TODO"""
        return [[v for k, v in r] for r in outsource]

    def out_pkeylist(self, outsource):
        """TODO

        :param outsource: TODO"""
        return [r[0][1] for r in outsource]

    def iter_pkeylist(self, outsource):
        """TODO

        :param outsource: TODO"""
        for r in outsource:
            yield r[0][1]

    def out_template(self,outsource,rowtemplate=None,joiner=''):
        result = []
        for r in outsource:
            result.append(gnrstring.templateReplace(rowtemplate,dict(r),safeMode=True))
        return joiner.join(result)

    def out_records(self, outsource,virtual_columns=None):
        """TODO

        :param outsource: TODO"""
        return [self.dbtable.record(r[0][1], mode='bag',virtual_columns=virtual_columns) for r in outsource]

    def iter_records(self, outsource):
        """TODO

        :param outsource: TODO"""
        for r in outsource:
            yield self.dbtable.record(r[0][1], mode='bag')

    def out_bag(self, outsource, recordResolver=False):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        b = Bag()
        headers = Bag()
        for k in self.columns:
            headers.addItem(k, None, _attributes=self.colAttrs.get(k, {}))
        b['headers'] = headers
        b['rows'] = self.buildAsBag(outsource, recordResolver)
        return b

    def buildAsBag(self, outsource, recordResolver):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        result = Bag()
        defaultTable = self.dbtable.fullname
        for j, row in enumerate(outsource):
            row = Bag(row)
            pkey = row.pop('pkey')
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey)

            nodecaption = self.dbtable.recordCaption(row)
            #fields, mask = self.dbtable.rowcaptionDecode()
            #cols = [(c, gnrstring.toText(row[c])) for c in fields]
            #if '$' in mask:
            #nodecaption = gnrstring.templateReplace(mask, dict(cols))
            #else:
            #nodecaption = mask % tuple([v for k,v in cols])

            result.addItem('%s' % spkey, row, nodecaption=nodecaption)
            if pkey and recordResolver:
                result['%s._' % spkey] = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                                  target_fld='%s.%s' % (defaultTable, self.dbtable.pkey),
                                                                  relation_value=pkey,
                                                                  joinConditions=self.joinConditions,
                                                                  sqlContextName=self.sqlContextName)

        return result

    def out_recordlist(self, outsource, recordResolver=True):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        result = Bag()
        content = None
        for j, row in enumerate(outsource):
            row = dict(row)
            content = self.dbtable.buildrecord(row)
            result.addItem('r_%i' % j, content, _pkey=row.get('pkey'))
        return result

    def out_baglist(self, outsource, recordResolver=False, labelIsPkey=False):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO
        :param caption: boolean. TODO"""
        result = Bag()
        for j, row in enumerate(outsource):
            row = dict(row)
            pkey = row.pop('pkey', None)
            if labelIsPkey:
                label = pkey
            else:
                label = 'r_%i' % j
            content = Bag(row)
            for k,v in list(content.items()):
                if self.dbtable.column(k) is not None and self.dbtable.column(k).attributes.get('dtype')=='X':
                    content[k] = Bag(content[k])
            if pkey is not None:
                content['_pkey'] = pkey
            result.addItem(label,content , _pkey=pkey)
        return result

    def out_selection(self, outsource, recordResolver=False, caption=False):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO
        :param caption: boolean. TODO"""
        result = Bag()
        content = ''
        for j, row in enumerate(outsource):
            row = dict(row)
            pkey = row.pop('pkey', None)
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey).replace('.', '_')
            if pkey and recordResolver:
                content = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                   target_fld='%s.%s' % (self.dbtable.fullname, self.dbtable.pkey),
                                                   relation_value=pkey,
                                                   joinConditions=self.joinConditions,
                                                   sqlContextName=self.sqlContextName)
            if caption:
                if isinstance(caption, str):
                    rowcaption = caption
                else:
                    rowcaption = None
                row['caption'] = self.dbtable.recordCaption(row, rowcaption=rowcaption)
            result.addItem('%s' % spkey, content,
                           _pkey=pkey, _attributes=row, _removeNullAttributes=False)
        return result

    def out_grid(self, outsource, recordResolver=True,**kwargs):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        return self.buildAsGrid(outsource, recordResolver,**kwargs)

    def buildAsGrid(self, outsource, recordResolver,virtual_columns=None,**kwargs):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        result = Bag()
        content = None
        for j, row in enumerate(outsource):
            row = Bag(row)
            pkey = row.pop('pkey')
            if not pkey:
                spkey = 'r_%i' % j
            else:
                spkey = gnrstring.toText(pkey)
            if pkey and recordResolver:
                content = SqlRelatedRecordResolver(db=self.db, cacheTime=-1, mode='bag',
                                                   target_fld='%s.%s' % (self.dbtable.fullname, self.dbtable.pkey),
                                                   relation_value=pkey, joinConditions=self.joinConditions,
                                                   virtual_columns=virtual_columns,
                                                   sqlContextName=self.sqlContextName)

            result.addItem('%s' % spkey.replace('.','_'), content, _pkey=spkey, _attributes=dict(row), _removeNullAttributes=False)
        return result

    def out_fullgrid(self, outsource, recordResolver=True):
        """TODO

        :param outsource: TODO
        :param recordResolver: boolean. TODO"""
        result = Bag()
        result['structure'] = self._buildGridStruct()
        result['data'] = self.buildAsGrid(outsource, recordResolver)
        return result

    def _buildGridStruct(self, examplerow=None):
        structure = Bag()
        r = structure.child('view').child('row')
        for colname in self.columns:
            if colname not in ('pkey', 'rowidx'):
                r.child('cell', childname=colname, **self._cellStructFromCol(colname, examplerow=examplerow))
        return structure

    def _cellStructFromCol(self, colname, examplerow=None):
        kwargs = dict(self.colAttrs.get(colname, {}))
        for k in ('tag','sql_formula','_owner_package','virtual_column','_sysfield','_sendback','group','readOnly'):
             kwargs.pop(k, None)
        kwargs['name'] = kwargs.pop('label', None)
        kwargs['field'] = colname
        size = kwargs.pop('size', None)
        size = kwargs.pop('print_width', size)
        kwargs['width'] = None
        kwargs['dtype'] = kwargs.pop('dataType', None)
        if not kwargs['dtype']:
            kwargs['dtype'] = GnrClassCatalog.convert().asTypedText(45)[-1]
        if size:
            if isinstance(size, str):
                if ':' in size:
                    size = size.split(':')[1]
            kwargs['width'] = '%iem' % int(int(size) * .7)
        return kwargs

    def out_xmlgrid(self, outsource):
        """Return a Bag

        :param outsource: TODO"""
        result = Bag()

        dataXml = []
        catalog = gnrclasses.GnrClassCatalog()
        #xmlheader = "<?xml version='1.0' encoding='UTF-8'?>\n"
        #structCellTmpl='<%(field)s  name="%(name)s" field="%(field)s" dataType="%(dataType)s" width="%(width)s" tag="cell"/>'
        dataCellTmpl = '<r_%i  %s/>'
        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        #structXml = '\n'.join([structCellTmpl % self._cellStructFromCol(colname) for colname in columns])
        #structure = '<structure><view_0 tag="view"><row_0 tag="row">%s</row_0></view_0></structure>' % structXml
        for row in outsource:
            row = dict(row)
            rowstring = ' '.join(
                    ['%s=%s' % (colname, saxutils.quoteattr(catalog.asTypedText(row[colname]))) for colname in columns])
            dataXml.append(dataCellTmpl % (row['rowidx'], rowstring))
        result['data'] = BagAsXml('\n'.join(dataXml))
        result['structure'] = self._buildGridStruct(row)
        #dataXml='<data>%s</data>' %
        # result = '%s\n<GenRoBag><result>%s\n%s</result></GenRoBag>' % (xmlheader,structure,dataXml)
        #result = BagAsXml('%s\n%s' % (structure,dataXml))
        return result

    @property
    def colHeaders(self):
        """TODO"""
        def translate(txt):
            return self.dbtable.db.localizer.translate(txt)


        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        headers = []
        for colname in columns:
            colattr = self.colAttrs.get(colname, dict())
            headers.append(translate(colattr.get('label', colname)))
        return headers

    def out_html(self, outsource):
        """TODO

        :param outsource: TODO"""

        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        result = ['<table><thead>',''.join(['<th>{}<th>'.format(h) for h in self.colHeaders]),'</thead>','<tbody>']
        for row in outsource:
            row = dict(row)
            result.append('<tr>{}</tr>'.format(''.join(['<td>{}<td>'.format('&nbsp;' if row[col] is None else row[col]) for col in columns])))
        result.append('</tbody></table>')
        return '\n'.join(result)

    def out_tabtext(self, outsource):
        """TODO

        :param outsource: TODO"""

        headers = self.colHeaders
        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        result = ['\t'.join(headers)]
        for row in outsource:
            r = dict(row)
            result.append(
                    '\t'.join([r[col].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ') for col in columns]))
        return '\n'.join(result)

    def out_xls(self, outsource, filepath=None,headers=None):
        """TODO

        :param outsource: TODO
        :param filePath: boolean. TODO. """
        try:
            import openpyxl # noqa: F401
            from gnr.core.gnrxls import XlsxWriter as ExcelWriter
        except ImportError:
            from gnr.core.gnrxls import XlsWriter as ExcelWriter

        columns = [c for c in self.columns if not c in ('pkey', 'rowidx')]
        coltypes = dict([(k, v['dataType']) for k, v in self.colAttrs.items()])
        if headers is None:
            headers = self.colHeaders
        elif headers is False:
            headers = columns
        writer = ExcelWriter(columns=columns, coltypes=coltypes,
                            headers=headers,
                            filepath=filepath,
                           font='Times New Roman',
                           format_float='#,##0.00', format_int='#,##0')
        writer(data=outsource)
