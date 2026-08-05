# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler.misc : CRUD, grid rendering, frozen selections, utilities
# Copyright (c)     : 2004 - 2026 Softwell sas - Milano
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

"""Miscellaneous operations mixin.

Provides :class:`MiscMixin` — a collection of small, autonomous
``@public_method`` endpoints grouped by domain:

- **CRUD**: insert, update, delete, duplicate, archive rows
- **Grid rendering**: transform selections for grid display
- **Frozen selections**: read/check/sum on pickled selections
- **Filesystem**: browse and delete files
- **Form**: auto-generate record forms
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import splitAndStrip, toText
from gnr.web.gnrwebstruct import cellFromField
from gnr.sql.gnrsql_exceptions import GnrSqlDeleteException


class MiscMixin:
    """Mixin for CRUD, grid rendering, frozen selections and utilities.

    All methods in this mixin are autonomous — they do not call other
    private methods within the handler (except ``_decodeWhereBag``
    from the core class, used by ``checkFreezedSelection``).
    """

    # -----------------------------------------------------------------------
    #  CRUD operations
    # -----------------------------------------------------------------------

    @public_method
    def counterFieldChanges(self, table: Optional[str] = None,
                            counterField: Optional[str] = None,
                            changes: Optional[list] = None) -> None:
        """Apply counter field value changes in batch.

        Args:
            table: Fully qualified table name.
            counterField: Name of the counter field to update.
            changes: List of dicts with ``_pkey`` and ``new`` keys.
        """
        updaterDict = dict([(d['_pkey'], d['new']) for d in changes])
        pkeys = list(updaterDict.keys())
        tblobj = self.db.table(table)

        def cb(r: dict) -> None:
            r[counterField] = updaterDict[r[tblobj.pkey]]

        _raw_update = True
        counterFieldAttr = tblobj.column(counterField).attributes
        if counterFieldAttr.get('triggerOnUpdate'):
            _raw_update = False
        tblobj.batchUpdate(cb, where='$%s IN:pkeys' % tblobj.pkey, pkeys=pkeys,
                           excludeDraft=False, _raw_update=_raw_update)
        self.db.commit()

    @public_method
    def deleteFileRows(self, files: Optional[Union[str, list]] = None,
                       **kwargs: Any) -> None:
        """Delete files from the storage filesystem.

        Args:
            files: A single file path (comma-separated) or a list of
                file paths.
        """
        if isinstance(files, str):
            files = files.split(',')
        for f in files:
            self.page.site.storageNode(f).delete()

    @public_method
    def saveEditedRows(self, table: Optional[str] = None,
                       changeset: Optional[Bag] = None,
                       commit: bool = True) -> Optional[Bag]:
        """Save rows edited in a grid (insert, update, delete).

        Args:
            table: Fully qualified table name.
            changeset: A :class:`Bag` with ``inserted``, ``updated``
                and ``deleted`` sub-bags.
            commit: Whether to commit after saving.

        Returns:
            A :class:`Bag` with ``wrongUpdates`` (concurrent edit
            conflicts) and ``insertedRecords`` (new pkeys).

        Note:
            REVIEW: Concurrent edit detection relies on comparing
            ``_loadedValue`` with the current DB value.  If the field
            was modified by another user, the update is silently skipped
            and added to ``wrongUpdates`` — the user is not explicitly
            notified of the conflict.
        """
        if not changeset:
            return
        inserted = changeset.pop('inserted')
        updated = changeset.pop('updated')
        if updated:
            updated = dict(updated.digest('#a._pkey,#v'))
        deletedNode = changeset.popNode('deleted')
        tblobj = self.db.table(table)
        pkeyfield = tblobj.pkey
        result = Bag()
        wrongUpdates = Bag()
        insertedRecords = Bag()

        def cb(row: dict) -> None:
            key = row[pkeyfield]
            c = updated.get(key)
            if c:
                for n in c:
                    if n.label in row:
                        if isinstance(n.value, Bag):
                            n.value.popAttributesFromNodes(['_loadedValue', 'dtype', '__old'])
                        elif '_loadedValue' in n.attr and row[n.label] != n.attr['_loadedValue']:
                            wrongUpdates[key] = row
                            return
                        row[n.label] = n.value
                    else:
                        if '_loadedValue' in n.attr:
                            row[n.label] = n.value

        if updated:
            pkeys = [pkey for pkey in updated.keys() if pkey]
            tblobj.batchUpdate(cb, _pkeys=pkeys, bagFields=True)
        if inserted:
            for k, r in list(inserted.items()):
                tblobj.insert(r)
                insertedRecords[k] = r[pkeyfield]
        if deletedNode:
            deleted = deletedNode.value
            unlinkfield = deletedNode.attr.get('unlinkfield')
            pkeys = [pkey for pkey in deleted.digest('#a._pkey') if pkey]
            self.deleteDbRows(table, pkeys=pkeys, unlinkfield=unlinkfield, commit=False)
        if commit:
            self.db.commit()
        result['wrongUpdates'] = wrongUpdates
        result['insertedRecords'] = insertedRecords
        return result

    @public_method
    def duplicateDbRows(self, table: str, pkeys: Optional[list] = None,
                        unlinkfield: Optional[str] = None,
                        commit: bool = True,
                        protectPkeys: Optional[list] = None,
                        **kwargs: Any) -> list:
        """Duplicate one or more records.

        Args:
            table: Fully qualified table name.
            pkeys: List of primary keys to duplicate.
            unlinkfield: Unused (signature kept for API compatibility).
            commit: Whether to commit.
            protectPkeys: Unused.

        Returns:
            List of new primary keys.

        Note:
            SMELL: ``unlinkfield`` and ``protectPkeys`` parameters are
            accepted but never used — they exist only for signature
            compatibility with ``deleteDbRows``.
        """
        if not self.page.checkTablePermission(table, 'readonly,ins'):
            raise self.page.exception('generic',
                                      description='Duplicate is not allowed in table % for user %s' % (table, self.user))
            # BUG: format string has ``%`` instead of ``%s`` for table name
        tblobj = self.db.table(table)
        result_pkeys = []
        for pkey in pkeys:
            record = tblobj.duplicateRecord(pkey, **kwargs)
            result_pkeys.append(record[tblobj.pkey])
        self.db.commit()
        return result_pkeys

    @public_method
    def deleteDbRows(self, table: str, pkeys: Optional[list] = None,
                     unlinkfield: Optional[str] = None,
                     commit: bool = True,
                     protectPkeys: Optional[list] = None,
                     **kwargs: Any) -> Optional[tuple[str, dict]]:
        """Delete or unlink multiple records from a table.

        When *unlinkfield* is set, records are unlinked (the field is
        set to ``None``) rather than deleted.  Records whose pkey is in
        *protectPkeys* are logically deleted instead of physically
        deleted.

        Args:
            table: Fully qualified table name.
            pkeys: List of primary keys.
            unlinkfield: Field to null-out instead of deleting.
            commit: Whether to commit.
            protectPkeys: Pkeys that should be logically deleted.

        Returns:
            ``None`` on success, or ``("delete_error", {"msg": ...})``
            on failure.

        Note:
            BUG: The format string in the permission check has ``%``
            instead of ``%s`` for the table name (same as
            ``duplicateDbRows``).
        """
        if not self.page.checkTablePermission(table, 'readonly,del'):
            raise self.page.exception('generic',
                                      description='Delete not allowed in table % for user %s' % (table, self.user))
            # BUG: format string has ``%`` instead of ``%s`` for table name
        try:
            tblobj = self.db.table(table)
            rows = tblobj.query(where='$%s IN :pkeys' % tblobj.pkey, pkeys=pkeys,
                                excludeLogicalDeleted=False,
                                for_update=True, addPkeyColumn=False, excludeDraft=False,
                                subtable='*').fetch()
            now = datetime.now()
            caption_field = tblobj.attributes.get('caption_field')
            if not rows:
                return
            labelfield = tblobj.name
            if caption_field and (caption_field in rows[0]):
                labelfield = caption_field
            deltitle = 'Unlink records' if unlinkfield else 'Delete records'
            for r in self.page.utils.quickThermo(rows, maxidx=len(rows), labelfield=labelfield, title=deltitle):
                if unlinkfield:
                    record = dict(r)
                    record[unlinkfield] = None
                    tblobj.update(record, r)
                else:
                    if protectPkeys and tblobj.logicalDeletionField and r[tblobj.pkey] in protectPkeys:
                        oldr = dict(r)
                        r[tblobj.logicalDeletionField] = now
                        tblobj.update(r, oldr)
                    else:
                        tblobj.delete(r)
            if commit:
                self.db.commit()

        except GnrSqlDeleteException as e:
            return ('delete_error', {'msg': e.message})

    @public_method
    def archiveDbRows(self, table: str, pkeys: Optional[list] = None,
                      unlinkfield: Optional[str] = None,
                      commit: bool = True,
                      protectPkeys: Optional[list] = None,
                      archiveDate: Optional[Any] = None,
                      **kwargs: Any) -> Optional[tuple[str, dict]]:
        """Logically delete (archive) multiple records.

        Sets the ``logicalDeletionField`` to *archiveDate* (or ``None``
        if no date is provided, which effectively un-archives).

        Args:
            table: Fully qualified table name.
            pkeys: List of primary keys.
            unlinkfield: Unused (signature compatibility).
            commit: Whether to commit.
            protectPkeys: Pkeys that should **not** be archived.
            archiveDate: The date to set as deletion timestamp.

        Returns:
            ``None`` on success, or ``("archive_error", {"msg": ...})``
            on failure.
        """
        try:
            tblobj = self.db.table(table)
            rows = tblobj.query(where='$%s IN :pkeys' % tblobj.pkey, pkeys=pkeys,
                                excludeLogicalDeleted=False,
                                for_update=True, addPkeyColumn=False, excludeDraft=False).fetch()
            ts = datetime(archiveDate.year, archiveDate.month, archiveDate.day) if archiveDate else None
            updated = False
            protectPkeys = protectPkeys or []
            for r in rows:
                if not (r[tblobj.pkey] in protectPkeys):
                    oldr = dict(r)
                    r[tblobj.logicalDeletionField] = ts
                    tblobj.update(r, oldr)
                    updated = True
            if commit and updated:
                self.db.commit()
        except GnrSqlDeleteException as e:
            return ('archive_error', {'msg': e.message})

    @public_method
    def insertRecord(self, table: Optional[str] = None,
                     record: Optional[Bag] = None,
                     **kwargs: Any) -> str:
        """Insert a new record.

        Args:
            table: Fully qualified table name.
            record: A :class:`Bag` with the record data.

        Returns:
            The primary key of the inserted record.
        """
        tblobj = self.db.table(table)
        newrecord = tblobj.newrecord(_fromRecord=record)
        extra_items = {k: v for k, v in record.items()}
        newrecord.update(extra_items)
        tblobj.insert(newrecord)
        self.db.commit()
        return newrecord[tblobj.pkey]

    @public_method
    def duplicateRecord(self, pkey: Optional[str] = None,
                        table: Optional[str] = None,
                        **kwargs: Any) -> str:
        """Duplicate a single record.

        Args:
            pkey: Primary key of the record to duplicate.
            table: Fully qualified table name.

        Returns:
            The primary key of the new record.
        """
        tblobj = self.db.table(table)
        record = tblobj.duplicateRecord(pkey, **kwargs)
        self.db.commit()
        return record[tblobj.pkey]

    @public_method
    def unifyRecords(self, sourcePkey: Optional[str] = None,
                     destPkey: Optional[str] = None,
                     table: Optional[str] = None,
                     **kwargs: Any) -> None:
        """Unify two records, merging the source into the destination.

        Args:
            sourcePkey: Primary key of the source (to be merged).
            destPkey: Primary key of the destination (to keep).
            table: Fully qualified table name.
        """
        tblobj = self.db.table(table)
        tblobj.unifyRecords(sourcePkey=sourcePkey, destPkey=destPkey)
        self.db.commit()

    @public_method
    def updateRecord(self, table: Optional[str] = None,
                     pkey: Optional[str] = None,
                     record: Optional[Bag] = None,
                     **kwargs: Any) -> None:
        """Update an existing record.

        Args:
            table: Fully qualified table name.
            pkey: Primary key of the record.
            record: A :class:`Bag` with the fields to update.
        """
        tblobj = self.db.table(table)
        with tblobj.recordToUpdate(pkey) as recToUpd:
            for k, v in record.items():
                recToUpd[k] = v
        self.db.commit()

    @public_method
    def saveRecord(self, table=None, pkey=None, data=None, **kwargs):
        tblobj = self.db.table(table)
        if pkey == '*newrecord*':
            tblobj.insert(tblobj.newrecord(**{k: v for k, v in data.items() if v is not None}))
        else:
            with tblobj.recordToUpdate(pkey) as recToUpd:
                for k, v in data.items():
                    recToUpd[k] = v
        self.db.commit()
        return dict(pkey=data[tblobj.pkey])

    @public_method
    def newRowsData(self, table: Optional[str] = None,
                    rows: Optional[list] = None) -> Bag:
        """Prepare default values for new rows.

        Args:
            table: Fully qualified table name.
            rows: List of row dicts with initial values.

        Returns:
            A :class:`Bag` with default-enriched rows.
        """
        result = Bag()
        tblobj = self.db.table(table)
        defaultValues = tblobj.defaultValues() or {}
        for i, r in enumerate(rows):
            row = Bag(r)
            for k, v in defaultValues.items():
                if row.get(k) is None:
                    row[k] = v
            tblobj.extendDefaultValues(row)
            result.addItem(f'r_{i}', row)
        return result

    @public_method
    def touchGridSelectedRows(self, table: Optional[str] = None,
                              pkeys: Optional[list] = None) -> None:
        """Touch (update timestamp) selected grid rows.

        Args:
            table: Fully qualified table name.
            pkeys: List of primary keys to touch.
        """
        self.db.table(table).touchRecords(_pkeys=pkeys)
        self.db.commit()

    @public_method
    def updateCheckboxPkeys(self, table: Optional[str] = None,
                            field: Optional[str] = None,
                            changesDict: Optional[dict] = None) -> None:
        """Apply checkbox toggle changes to multiple records.

        Args:
            table: Fully qualified table name.
            field: The boolean field to update.
            changesDict: A dict mapping pkey to new boolean value,
                plus an optional ``_fields`` key listing all fields
                to reset.
        """
        if not changesDict:
            return
        tblobj = self.db.table(table)
        fields = changesDict.pop('_fields', None)
        if not fields:
            fields = [field]

        def cb(row: dict) -> None:
            for f in fields:
                row[f] = changesDict[row[tblobj.pkey]] if f == field else False

        tblobj.batchUpdate(cb, where='$%s IN :pkeys' % tblobj.pkey, pkeys=list(changesDict.keys()))
        self.db.commit()

    # -----------------------------------------------------------------------
    #  Grid rendering
    # -----------------------------------------------------------------------

    def gridSelectionData(self, selection: Any, outsource: Any,
                          recordResolver: bool, numberedRows: bool,
                          logicalDeletionField: Optional[str],
                          _addClassesDict: Optional[dict] = None) -> Bag:
        """Transform a selection generator into a :class:`Bag` for grid display.

        Args:
            selection: The source selection.
            outsource: Generator or iterable of row dicts.
            recordResolver: Whether to add resolver attributes for
                record-level lazy loading.
            numberedRows: Use numeric keys (``r_0``, ``r_1``, ...).
            logicalDeletionField: Name of the logical deletion field.
            _addClassesDict: Mapping of field names to CSS classes to
                add based on field values.

        Returns:
            A :class:`Bag` suitable for client-side grid rendering.
        """
        result = Bag()
        for j, row in enumerate(outsource):
            row = dict(row)
            _customClasses = (row.get('_customClasses', '') or '').split(' ')
            pkey = row.pop('pkey', None)
            isDeleted = row.pop('_isdeleted', None)
            if isDeleted:
                _customClasses.append('logicalDeleted')

            if _addClassesDict:
                for fld, _class in list(_addClassesDict.items()):
                    val = row.get(fld)
                    if val in (None, False, ''):
                        continue
                    if isinstance(_class, dict):
                        _class = _class.get(row[fld])
                    else:
                        _class = row[fld] if _class is True else _class
                    if _class:
                        _customClasses.append(_class)
            if numberedRows or not pkey:
                row_key = 'r_%i' % j
            else:
                row_key = toText(pkey).replace('.', '_')
            kw = dict(_pkey=pkey or row_key,
                      _attributes=row,
                      _removeNullAttributes=False,
                      _customClasses=' '.join(_customClasses))
            if recordResolver:
                kw.update(_target_fld='%s.%s' % (selection.dbtable.fullname, selection.dbtable.pkey),
                          _relation_value=pkey,
                          _resolver_name='relOneResolver')
            value = None
            attributes = kw.get('_attributes')
            colAttrs = selection.colAttrs
            for k, v in list(attributes.items()):
                if v and colAttrs.get(k, {}).get('dataType') == 'X':
                    attributes[k] = "%s::X" % v
            if attributes and '__value__' in attributes:
                value = attributes.pop('__value__')
            result.appendNode(row_key, value, **kw)
        return result

    @public_method
    def getFieldcellPars(self, field: Optional[str] = None,
                         table: Optional[str] = None) -> Bag:
        """Return cell parameters for a field (used by grid column setup).

        Args:
            field: Field path.
            table: Fully qualified table name.

        Returns:
            A :class:`Bag` with cell configuration parameters.
        """
        tableobj = self.db.table(table)
        cellpars = cellFromField(field, tableobj, checkPermissions=self.page.permissionPars)
        cellpars['field'] = field
        return Bag(cellpars)

    def gridSelectionStruct(self, selection: Any) -> Bag:
        """Generate a view/row/cell structure :class:`Bag` from a selection.

        Args:
            selection: The source selection whose ``colAttrs`` describe
                the columns.

        Returns:
            A :class:`Bag` with ``view > row > cell`` hierarchy.
        """
        structure = Bag()
        r = structure.child('view').child('row')
        for colname in selection.columns:
            if ((colname != 'pkey') and (colname != 'rowidx')):
                kwargs = dict(selection.colAttrs.get(colname, {}))
                kwargs.pop('tag', None)
                kwargs['name'] = kwargs.pop('label')
                if kwargs['dataType'] == 'D':
                    kwargs['format_date'] = 'short'
                size = kwargs.pop('size', None)
                size = kwargs.pop('print_width', size)
                if size:
                    if isinstance(size, str):
                        if ':' in size:
                            size = size.split(':')[1]
                    size = int(size)
                    if size < 3:
                        width = size * 1.1
                    if size < 6:  # BUG: should be ``elif`` — when size < 3 both branches execute
                        width = size
                    elif size < 10:
                        width = size * .8
                    elif size < 20:
                        width = size * .7
                    else:
                        width = size * .6
                    kwargs['width'] = '%iem' % (1 + int(int(width) * .7))
                r.child('cell', childname=colname, field=colname, **kwargs)
        return structure

    # -----------------------------------------------------------------------
    #  Frozen selections
    # -----------------------------------------------------------------------

    @public_method
    def freezedSelectionPkeys(self, table: Optional[str] = None,
                              selectionName: Optional[str] = None,
                              caption_field: Optional[str] = None) -> list:
        """Return primary keys from a frozen selection.

        Args:
            table: Fully qualified table name.
            selectionName: Name of the frozen selection.
            caption_field: When set, return dicts with ``pkey`` and
                ``caption`` instead of plain pkeys.

        Returns:
            A list of pkeys (or dicts).
        """
        selection = self.page.unfreezeSelection(dbtable=table, name=selectionName)
        l = selection.output('dictlist')
        return [dict(pkey=r['pkey'], caption=r['caption_field']) if caption_field else r['pkey'] for r in l]

    @public_method
    def sumOnFreezedSelection(self, selectionName: Optional[str] = None,
                              where: Optional[str] = None,
                              table: Optional[str] = None,
                              sum_column: Optional[str] = None,
                              **kwargs: Any) -> Any:
        """Sum a column on a frozen selection.

        Args:
            selectionName: Name of the frozen selection.
            where: Unused (signature compatibility).
            table: Fully qualified table name.
            sum_column: Column to sum.

        Returns:
            The sum value, or ``0`` if the selection is missing.
        """
        selection = self.page.unfreezeSelection(dbtable=table, name=selectionName)
        if selection is None:
            return 0
        return selection.sum(sum_column)

    @public_method
    def checkFreezedSelection(self, changelist: Optional[list] = None,
                              selectionName: Optional[str] = None,
                              where: Optional[Any] = None,
                              table: Optional[str] = None,
                              **kwargs: Any) -> bool:
        """Check if a frozen selection needs to be refreshed.

        Examines a list of database change events (insert/update/delete)
        and determines whether any of them affect the frozen selection.

        Args:
            changelist: List of change event dicts with ``dbevent``
                (``"I"``/``"U"``/``"D"``) and ``pkey`` keys.
            selectionName: Name of the frozen selection.
            where: SQL WHERE clause (may be a :class:`Bag`).
            table: Fully qualified table name.

        Returns:
            ``True`` if the selection should be refreshed.
        """
        selection = self.page.unfreezeSelection(dbtable=table, name=selectionName)
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
            where, kwargs = self._decodeWhereBag(tblobj, where, kwargs)
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

    # -----------------------------------------------------------------------
    #  Filesystem
    # -----------------------------------------------------------------------

    @public_method
    def getFileSystemSelection(self, folders: Optional[str] = None,
                               ext: Optional[str] = None,
                               include: Optional[str] = None,
                               exclude: Optional[str] = None,
                               columns: Optional[str] = None,
                               hierarchical: bool = False,
                               applymethod: Optional[str] = None,
                               **kwargs: Any) -> Union[Bag, tuple[Bag, dict]]:
        """Browse files from the storage filesystem as a selection.

        Args:
            folders: Comma-separated list of storage folder paths.
            ext: File extension filter.
            include: Include pattern.
            exclude: Exclude pattern.
            columns: Additional columns to read from XML files.
            hierarchical: Return the hierarchical tree rather than
                a flat list.
            applymethod: Post-processing method name.

        Returns:
            A :class:`Bag` (or tuple with attributes) representing
            the file listing.
        """
        files = Bag()
        resultAttributes = dict()
        from gnr.lib.services.storage import StorageResolver

        def setFileAttributes(node: Any, **kwargs: Any) -> None:
            attr = node.attr
            if not node.value and node.attr:
                abs_path = attr['abs_path']
                attr['_pkey'] = abs_path
                attr['created_ts'] = datetime.fromtimestamp(attr['mtime'])
                attr['changed_ts'] = datetime.fromtimestamp(attr['mtime'])
                if columns and attr['file_ext'].lower() == 'xml':
                    with self.page.site.storageNode(abs_path).open('rb') as f:
                        b = Bag(f)
                    for c in columns.split(','):
                        c = c.replace('$', '')
                        attr[c] = b[c]

        for f in folders.split(','):
            files[f] = StorageResolver(self.page.site.storageNode(f), include=include,
                                       exclude=exclude, ext=ext, _page=self.page)()
        files.walk(setFileAttributes, _mode='')
        if hierarchical:
            return files
        result = Bag([('r_%i' % i, None, t[1].attr) for i, t in enumerate(files.getIndex())
                      if t[1].attr and t[1].attr['file_ext'] != 'directory'])
        if applymethod:
            applyPars = self._getApplyMethodPars(kwargs)
            applyresult = self.page.getPublicMethod('rpc', applymethod)(result, **applyPars)
            if applyresult:
                resultAttributes.update(applyresult)
        return result, resultAttributes

    # -----------------------------------------------------------------------
    #  Form
    # -----------------------------------------------------------------------

    def _relPathToCaption(self, table: str, relpath: str) -> str:
        """Convert a relation path to a human-readable caption.

        Args:
            table: Fully qualified table name.
            relpath: Dot-separated relation path.

        Returns:
            A colon-separated caption string.
        """
        if not relpath:
            return ''
        tbltree = self.db.relationExplorer(table, dosort=False, pyresolver=True)
        fullcaption = tbltree.cbtraverse(relpath, lambda node: self.page._(node.getAttr('name_long')))
        return ':'.join(fullcaption)

    def rpc_getRecordForm(self, dbtable: Optional[str] = None,
                          fields: Optional[str] = None,
                          **kwargs: Any) -> None:
        """Generate a record form and send it to the client.

        Args:
            dbtable: Fully qualified table name.
            fields: Comma-separated list of fields to include.

        Note:
            SMELL: Calls ``self.getRecordForm`` which is not defined
            anywhere in the handler — likely a leftover method that
            would only work if the page itself defines it.
        """
        self.getRecordForm(self.newSourceRoot(), dbtable=dbtable, fields=fields, **kwargs)

    def formAuto(self, pane: Any, table: str, columns: Union[str, list] = '',
                 cols: int = 2) -> None:
        """Auto-generate a form from a table's columns.

        Args:
            pane: The content pane where the form is rendered.
            table: Fully qualified table name.
            columns: Column list (comma-separated string or list).
                When empty, all non-reserved, non-blob columns are used.
            cols: Number of columns in the form layout.
        """
        fb = pane.formbuilder(cols=cols)
        tblobj = self.db.table(table)
        if not columns:
            columns = [colname for colname, col in list(tblobj.columns.items()) if
                       not col.isReserved and not col.dtype == 'X' and not col.dtype == 'Z']
        elif isinstance(columns, str):
            columns = splitAndStrip(columns)
        fb.placeFields(','.join(columns))
