# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrfreezedselections : proxy for freezed selection lifecycle
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy


class GnrFreezedSelections(GnrBaseProxy):

    def freezeSelection(self, selection, name, **kwargs):
        """Freeze a selection to disk.

        :param selection: the SqlSelection to freeze
        :param name: the document name used as freeze path"""
        path = self.pageLocalDocument(name)
        selection.freeze(path, autocreate=True, **kwargs)
        return path

    def freezeSelectionUpdate(self, selection):
        """Update the frozen files for a previously frozen selection.

        :param selection: the SqlSelection to update"""
        selection.freezeUpdate()

    def unfreezeSelection(self, dbtable=None, name=None, page_id=None):
        """Restore a previously frozen selection from disk.

        :param dbtable: specify the :ref:`database table <table>`. More information in the
                        :ref:`dbtable` section (:ref:`dbselect_examples_simple`)
        :param name: the document name used as freeze path
        :param page_id: optional page_id override"""
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.db.table(dbtable)
        selection = self.db.unfreezeSelection(self.pageLocalDocument(name, page_id=page_id))
        if dbtable and selection is not None:
            assert dbtable == selection.dbtable, 'unfrozen selection does not belong to the given table'
        return selection

    def freezedPkeys(self, dbtable=None, name=None, page_id=None):
        """Return the list of primary keys from a frozen selection.

        :param dbtable: the database table
        :param name: the document name used as freeze path
        :param page_id: optional page_id override"""
        assert name, 'name is mandatory'
        if isinstance(dbtable, str):
            dbtable = self.db.table(dbtable)
        return self.db.freezedPkeys(self.pageLocalDocument(name, page_id=page_id))

    @public_method
    def getUserSelection(self, selectionName=None, selectedRowidx=None, filterCb=None, columns=None,
                         sortBy=None, condition=None, table=None, condition_args=None, limit=None):
        """Return a previously frozen selection, optionally filtered/sorted/re-queried.

        :param selectionName: the name of the frozen selection
        :param selectedRowidx: comma-separated row indices to filter
        :param filterCb: a public method name to use as filter callback
        :param columns: columns to re-query with
        :param sortBy: sort expression
        :param condition: additional WHERE condition
        :param table: the database table name
        :param condition_args: arguments for the condition
        :param limit: limit the number of rows"""
        assert selectionName, 'selectionName is mandatory'
        page_id = self.sourcepage_id or self.page_id
        if isinstance(table, str):
            table = self.db.table(table)
        selection = self.unfreezeSelection(dbtable=table, name=selectionName, page_id=page_id)
        table = table or selection.dbtable
        if not columns and limit is not None:
            qpars = dict(selection.querypars)
            selection_limit = qpars.get('limit')
            if selection_limit != limit:
                qpars['limit'] = limit
                selection = table.query(**qpars).selection(_aggregateRows=True)
        if filterCb:
            filterCb = self.getPublicMethod('rpc', filterCb)
            selection.filter(filterCb)
        elif selectedRowidx:
            if isinstance(selectedRowidx, str):
                selectedRowidx = [int(x) for x in selectedRowidx.split(',')]
                selectedRowidx = set(selectedRowidx)
            selection.filter(lambda r: r['rowidx'] in selectedRowidx)
        if sortBy:
            selection.sort(sortBy)
        if not columns:
            return selection
        if columns == 'pkey':
            return selection.output('pkeylist')
        condition_args = condition_args or {}
        pkeys = selection.output('pkeylist')
        where = 't0.%s in :pkeys' % table.pkey
        if condition:
            where = '%s AND %s' % (where, condition)
        selection = table.query(columns=columns, where=where,
                                pkeys=pkeys, addPkeyColumn=False,
                                excludeLogicalDeleted=False,
                                ignorePartition=True, subtable='*',
                                excludeDraft=False, limit=limit,
                                **condition_args).selection(_aggregateRows=True)
        if sortBy:
            selection.sort(sortBy)
        return selection

    @public_method
    def freezedSelectionPkeys(self, table=None, selectionName=None, caption_field=None):
        """Return pkeys (and optionally captions) from a frozen selection.

        :param table: the database table
        :param selectionName: the name of the frozen selection
        :param caption_field: if truthy, return dicts with pkey and caption"""
        selection = self.unfreezeSelection(dbtable=table, name=selectionName)
        l = selection.output('dictlist')
        return [dict(pkey=r['pkey'], caption=r['caption_field']) if caption_field else r['pkey'] for r in l]

    @public_method
    def sumOnFreezedSelection(self, selectionName=None, where=None, table=None, sum_column=None, **kwargs):
        """Return the sum of a column on a frozen selection.

        :param selectionName: the name of the frozen selection
        :param where: the sql WHERE clause
        :param table: the database table
        :param sum_column: the column to sum"""
        selection = self.unfreezeSelection(dbtable=table, name=selectionName)
        if selection is None:
            return 0
        return selection.sum(sum_column)

    @public_method
    def checkFreezedSelection(self, changelist=None, selectionName=None, where=None, table=None, **kwargs):
        """Check if a frozen selection needs to be refreshed given a list of DB changes.

        :param changelist: list of dicts with 'dbevent' and 'pkey' keys
        :param selectionName: the name of the frozen selection
        :param where: the sql WHERE clause
        :param table: the database table"""
        selection = self.unfreezeSelection(dbtable=table, name=selectionName)
        if selection is None:
            return False
        eventdict = {}
        for change in changelist:
            eventdict.setdefault(change['dbevent'], []).append(change['pkey'])
        deleted = eventdict.get('D', [])
        if deleted:
            if bool([r for r in selection.data if r['pkey'] in deleted]):
                return True
        updated = eventdict.get('U', [])
        if updated:
            if bool([r for r in selection.data if r['pkey'] in updated]):
                return True
        inserted = eventdict.get('I', [])
        kwargs.pop('where_attr', None)
        tblobj = self.db.table(table)
        wherelist = ['( $%s IN :_pkeys )' % tblobj.pkey]
        if isinstance(where, Bag):
            where, kwargs = self.page.app._decodeWhereBag(tblobj, where, kwargs)
        if where:
            wherelist.append(' ( %s ) ' % where)
        condition = kwargs.pop('condition', None)
        if condition:
            wherelist.append(condition)
        where = ' AND '.join(wherelist)
        kwargs.pop('columns', None)
        kwargs['limit'] = 1
        if bool(tblobj.query(where=where, _pkeys=inserted + updated, **kwargs).fetch()):
            return True
        return False
