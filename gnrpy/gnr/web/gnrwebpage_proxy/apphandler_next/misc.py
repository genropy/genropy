# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module apphandler_next.misc : CRUD, grid rendering, frozen selections, utilities
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

- **record writes**: insert, update, save, duplicate, unify, the grid changeset
- **row operations**: delete, archive, duplicate, touch, checkboxes, files
- **frozen selections**: read, check and sum on a pickled selection
- **grid rendering**: the data Bag and the structure Bag of a selection
- **file system**: browse a storage folder as a selection

Everything that needs only the table and the database is on the app level
write proxy ``tblobj.writeHandler()``
(:class:`gnr.app.gnrsqltable_proxy.write.WriteHandler`).  What stays here is
what needs the page: the table permission checks, the progress thermo, the
frozen selections, the storage service and the rpc method lookup.  The grid
rendering stays too, for the opposite reason: it needs neither the page nor the
table, only the selection, so a table proxy is not its place either.

This module is the copy that receives new work.  The module of the same
name under ``gnr.web.gnrwebpage_proxy.apphandler`` is frozen and is never
imported from here.

The methods with no caller anywhere in the tree are not part of the copy:
``rpc_getRecordForm`` and ``formAuto``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toText
from gnr.lib.services.storage import StorageResolver
from gnr.web.gnrwebstruct import cellFromField
from gnr.sql.gnrsql_exceptions import GnrSqlDeleteException


class MiscMixin:
    """Mixin for record writes, row operations, grids, frozen selections, files.

    Every method is an entry point of its own: none of them calls another one,
    except ``saveEditedRows``, which deletes through ``deleteDbRows`` because a
    page may override it, and ``checkFreezedSelection``, which decodes a where
    bag through ``_decodeWhereBag`` of the core class.
    """

    # -----------------------------------------------------------------------
    #  Helpers on the page
    # -----------------------------------------------------------------------

    def _checkTableWritePermission(self, table: str, permissions: str,
                                   action: str) -> None:
        """Raise the page exception when *table* is closed to *permissions*.

        Args:
            table: fully qualified table name.
            permissions: the comma separated permissions to check.
            action: the word the message opens with, ``Delete`` or ``Duplicate``.

        Raises:
            The page ``generic`` exception, when the permission is denied.
        """
        if self.page.checkTablePermission(table, permissions):
            return
        raise self.page.exception(
            'generic',
            description='%s is not allowed in table %s for user %s' % (
                action, table, self.user))

    def _quickThermo(self, rows: list, labelfield: str, title: str) -> Any:
        """Wrap *rows* in the progress bar the client shows while they change.

        Args:
            rows: the rows the flow is about to write.
            labelfield: the column whose value names the current row.
            title: the title of the progress box.

        Returns:
            A generator yielding the same rows.
        """
        return self.page.utils.quickThermo(rows, maxidx=len(rows),
                                           labelfield=labelfield, title=title)

    # -----------------------------------------------------------------------
    #  Record writes
    # -----------------------------------------------------------------------

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

        Note:
            ``kwargs`` is accepted and never read.
        """
        return self.db.table(table).writeHandler().insertRecord(record)

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

        Note:
            ``kwargs`` is accepted and never read.
        """
        self.db.table(table).writeHandler().updateRecord(pkey, record)

    @public_method
    def saveRecord(self, table: Optional[str] = None,
                   pkey: Optional[str] = None,
                   data: Optional[Bag] = None,
                   **kwargs: Any) -> dict:
        """Save the record a form sent, inserting it when it is new.

        Args:
            table: Fully qualified table name.
            pkey: Primary key of the record, or ``'*newrecord*'``.
            data: The fields the form sent.

        Returns:
            ``{'pkey': <the pkey of the saved record>}``.

        Note:
            The frozen handler returns the pkey *data* carries, which on the
            insert branch is the one the client did not have; the copy returns
            the pkey the insert produced.  ``kwargs`` is accepted and never
            read.
        """
        saved_pkey = self.db.table(table).writeHandler().saveRecord(pkey, data)
        return dict(pkey=saved_pkey)

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

        Note:
            No permission check, unlike ``duplicateDbRows``, which does the same
            thing in bulk.  ``kwargs`` is forwarded to the table.
        """
        return self.db.table(table).writeHandler().duplicateRecord(pkey, **kwargs)

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

        Note:
            ``kwargs`` is accepted and never read.
        """
        self.db.table(table).writeHandler().unifyRecords(sourcePkey, destPkey)

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
            conflicts) and ``insertedRecords`` (new pkeys), or ``None`` when
            *changeset* is empty.

        Note:
            The three sub-bags are popped out of *changeset*, so the caller's
            Bag comes back empty.  A row whose ``_loadedValue`` no longer
            matches the database is abandoned whole and lands in
            ``wrongUpdates``; nothing tells the user that it did.
        """
        if not changeset:
            return
        inserted = changeset.pop('inserted')
        updated = changeset.pop('updated')
        if updated:
            updated = dict(updated.digest('#a._pkey,#v'))
        deletedNode = changeset.popNode('deleted')
        wrongUpdates, insertedRecords = self.db.table(table).writeHandler(
            ).applyEditedRows(updated=updated, inserted=inserted)
        if deletedNode:
            pkeys = [pkey for pkey in deletedNode.value.digest('#a._pkey') if pkey]
            self.deleteDbRows(table, pkeys=pkeys,
                              unlinkfield=deletedNode.attr.get('unlinkfield'),
                              commit=False)
        if commit:
            self.db.commit()
        result = Bag()
        result['wrongUpdates'] = wrongUpdates
        result['insertedRecords'] = insertedRecords
        return result

    @public_method
    def newRowsData(self, table: Optional[str] = None,
                    rows: Optional[list] = None) -> Bag:
        """Prepare default values for new rows.

        Args:
            table: Fully qualified table name.
            rows: List of row dicts with initial values.

        Returns:
            A :class:`Bag` of the rows, keyed ``r_0``, ``r_1``, ..., each one
            with the table defaults filled in where the caller left ``None``.
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
            result.addItem('r_%i' % i, row)
        return result

    @public_method
    def counterFieldChanges(self, table: Optional[str] = None,
                            counterField: Optional[str] = None,
                            changes: Optional[list] = None) -> None:
        """Apply counter field value changes in batch.

        Args:
            table: Fully qualified table name.
            counterField: Name of the counter field to update.
            changes: List of dicts with ``_pkey`` and ``new`` keys.

        Note:
            No permission check.  The update is raw unless the counter column
            declares ``triggerOnUpdate``, so the triggers do not run by default.
        """
        self.db.table(table).writeHandler().counterFieldChanges(counterField,
                                                                changes)

    # -----------------------------------------------------------------------
    #  Row operations
    # -----------------------------------------------------------------------

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
        deleted, on a table that has a logical deletion field.

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
            The failure branch is unreachable, and would raise if it were
            reached: the exception class it catches is the homonym of the wrong
            module, and ``e.message`` does not exist.  Both are reproduced from
            the frozen handler on purpose, see ``bugs_misc.md``.  ``kwargs`` is
            accepted and never read.
        """
        self._checkTableWritePermission(table, 'readonly,del', 'Delete')
        try:
            writer = self.db.table(table).writeHandler()
            rows = writer.rowsToDelete(pkeys)
            if not rows:
                return
            title = 'Unlink records' if unlinkfield else 'Delete records'
            writer.deleteRows(self._quickThermo(rows,
                                                writer.deleteLabelField(rows),
                                                title),
                              unlinkfield=unlinkfield,
                              protectPkeys=protectPkeys, commit=commit)
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
            unlinkfield: Accepted and never read.
            commit: Whether to commit, when at least one row changed.
            protectPkeys: Pkeys that should **not** be archived — the opposite
                of what the same parameter means in ``deleteDbRows``.
            archiveDate: The date to set as deletion timestamp.

        Returns:
            ``None`` on success, or ``("archive_error", {"msg": ...})``
            on failure.

        Note:
            No permission check at all, unlike ``deleteDbRows``.  The failure
            branch carries the same two defects as that one.  ``kwargs`` is
            accepted and never read.
        """
        try:
            self.db.table(table).writeHandler().archiveRows(
                pkeys, archiveDate=archiveDate, protectPkeys=protectPkeys,
                commit=commit)
        except GnrSqlDeleteException as e:
            return ('archive_error', {'msg': e.message})

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
            unlinkfield: Accepted and never read.
            commit: Accepted and never read — the duplication always commits.
            protectPkeys: Accepted and never read.

        Returns:
            List of new primary keys.

        Note:
            The three unread parameters are there for signature symmetry with
            ``deleteDbRows``.  ``commit`` is one of them in the frozen handler
            and stays one here, see ``bugs_misc.md``.
        """
        self._checkTableWritePermission(table, 'readonly,ins', 'Duplicate')
        return self.db.table(table).writeHandler().duplicateRecords(pkeys,
                                                                    **kwargs)

    @public_method
    def deleteFileRows(self, files: Optional[Union[str, list]] = None,
                       **kwargs: Any) -> None:
        """Delete files from the storage filesystem.

        Args:
            files: A single file path (comma-separated) or a list of
                file paths.

        Note:
            No table, no permission check and no confirmation: whatever the
            client names is deleted.  ``kwargs`` is accepted and never read.
        """
        if isinstance(files, str):
            files = files.split(',')
        for f in files:
            self.page.site.storageNode(f).delete()

    @public_method
    def touchGridSelectedRows(self, table: Optional[str] = None,
                              pkeys: Optional[list] = None) -> None:
        """Touch (update timestamp) selected grid rows.

        Args:
            table: Fully qualified table name.
            pkeys: List of primary keys to touch.

        Note:
            No permission check.
        """
        self.db.table(table).writeHandler().touchRows(pkeys)

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

        Note:
            ``_fields`` is popped out of the caller's dict, because the pkeys
            are the keys that remain.  With more than one field the semantic is
            a radio group: every other field of the list is set to ``False``.
        """
        if not changesDict:
            return
        fields = changesDict.pop('_fields', None)
        self.db.table(table).writeHandler().updateCheckboxPkeys(
            field, changesDict, fields=fields)

    # -----------------------------------------------------------------------
    #  Frozen selections
    # -----------------------------------------------------------------------

    def _freezedSelection(self, table: Optional[str],
                          selectionName: Optional[str]) -> Any:
        """The frozen selection *selectionName* of *table*, or ``None``.

        Args:
            table: Fully qualified table name.
            selectionName: Name the selection was frozen under.

        Returns:
            The unpickled selection, or ``None`` when there is no such file.
        """
        return self.page.unfreezeSelection(dbtable=table, name=selectionName)

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
            A list of pkeys, or of ``{'pkey': ..., 'caption': ...}`` dicts.

        Note:
            The frozen handler reads the caption under the literal key
            ``'caption_field'`` and raises ``KeyError`` for every real column
            name; the copy reads the column *caption_field* names.
        """
        rows = self._freezedSelection(table, selectionName).output('dictlist')
        if not caption_field:
            return [r['pkey'] for r in rows]
        return [dict(pkey=r['pkey'], caption=r[caption_field]) for r in rows]

    @public_method
    def sumOnFreezedSelection(self, selectionName: Optional[str] = None,
                              where: Optional[str] = None,
                              table: Optional[str] = None,
                              sum_column: Optional[str] = None,
                              **kwargs: Any) -> Any:
        """Sum a column on a frozen selection.

        Args:
            selectionName: Name of the frozen selection.
            where: Accepted and never read.
            table: Fully qualified table name.
            sum_column: Column to sum.

        Returns:
            The list ``selection.sum`` returns, one item per column, or the
            integer ``0`` when the selection is missing.
        """
        selection = self._freezedSelection(table, selectionName)
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
        selection = self._freezedSelection(table, selectionName)
        if selection is None:
            return False
        eventdict: dict[str, list] = {}
        for change in changelist:
            eventdict.setdefault(change['dbevent'], []).append(change['pkey'])
        selection_pkeys = set(r['pkey'] for r in selection.data)
        for dbevent in ('D', 'U'):
            if selection_pkeys.intersection(eventdict.get(dbevent, [])):
                return True
        candidates = eventdict.get('I', []) + eventdict.get('U', [])
        return self._freezedSelectionProbe(table, where, candidates, kwargs)

    def _freezedSelectionProbe(self, table: Optional[str], where: Any,
                               pkeys: list, kwargs: dict) -> bool:
        """Does any row of *pkeys* match the filter the frozen selection used?

        The WHERE is the pkeys, plus the caller's *where* — decoded first when
        it is a Bag — plus the caller's ``condition``.  ``where_attr`` and
        ``columns`` are dropped and the limit is forced to one row: the answer
        is a yes or a no, not a result set.

        Args:
            table: Fully qualified table name.
            where: The filter, a string or a :class:`Bag`.
            pkeys: The pkeys to probe.
            kwargs: The remaining query parameters; it is modified in place.

        Returns:
            ``True`` when at least one row matches.
        """
        tblobj = self.db.table(table)
        kwargs.pop('where_attr', None)
        kwargs.pop('columns', None)
        wherelist = ['( $%s IN :_pkeys )' % tblobj.pkey]
        if isinstance(where, Bag):
            where, kwargs = self._decodeWhereBag(tblobj, where, kwargs)
        if where:
            wherelist.append(' ( %s ) ' % where)
        condition = kwargs.pop('condition', None)
        if condition:
            wherelist.append(condition)
        kwargs['limit'] = 1
        return bool(tblobj.query(where=' AND '.join(wherelist), _pkeys=pkeys,
                                 **kwargs).fetch())

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
            logicalDeletionField: Accepted and never read: the flag the rows
                carry is ``_isdeleted``.
            _addClassesDict: Mapping of field names to CSS classes to
                add based on field values.

        Returns:
            A :class:`Bag` suitable for client-side grid rendering.
        """
        result = Bag()
        for j, row in enumerate(outsource):
            row = dict(row)
            pkey = row.pop('pkey', None)
            isDeleted = row.pop('_isdeleted', None)
            row_key = self._gridRowKey(j, pkey, numberedRows)
            kw = dict(_pkey=pkey or row_key,
                      _attributes=row,
                      _removeNullAttributes=False,
                      _customClasses=self._gridRowClasses(row, isDeleted,
                                                          _addClassesDict))
            if recordResolver:
                kw.update(_target_fld='%s.%s' % (selection.dbtable.fullname,
                                                 selection.dbtable.pkey),
                          _relation_value=pkey,
                          _resolver_name='relOneResolver')
            value = None
            attributes = selection.typedAttributes(kw.get('_attributes'))
            if attributes and '__value__' in attributes:
                value = attributes.pop('__value__')
            result.appendNode(row_key, value, **kw)
        return result

    @staticmethod
    def _gridRowKey(row_index: int, pkey: Optional[str],
                    numberedRows: bool) -> str:
        """The node label of one grid row.

        The position when *numberedRows* asks for it or the row has no pkey,
        the pkey with the dots turned into underscores otherwise, because a dot
        would open a level in the Bag.

        Args:
            row_index: The position of the row in the selection.
            pkey: The pkey of the row, when it has one.
            numberedRows: Whether the caller asked for positional keys.

        Returns:
            The node label.
        """
        if numberedRows or not pkey:
            return 'r_%i' % row_index
        return toText(pkey).replace('.', '_')

    @staticmethod
    def _gridRowClasses(row: dict, isDeleted: Any,
                        addClassesDict: Optional[dict]) -> str:
        """The CSS classes of one grid row, as a space separated string.

        The classes the row already carries, plus ``logicalDeleted`` when it is
        logically deleted, plus one class per entry of *addClassesDict* whose
        field has a value: a dict entry is a lookup table on that value, ``True``
        means the value is itself the class name, anything else is the class.

        Args:
            row: The row, without its pkey and its deletion flag.
            isDeleted: The ``_isdeleted`` flag popped out of the row.
            addClassesDict: The per field class specification, or ``None``.

        Returns:
            The class list of the row.
        """
        classes = (row.get('_customClasses', '') or '').split(' ')
        if isDeleted:
            classes.append('logicalDeleted')
        for fld, _class in list((addClassesDict or {}).items()):
            value = row.get(fld)
            if value in (None, False, ''):
                continue
            if isinstance(_class, dict):
                _class = _class.get(value)
            elif _class is True:
                _class = value
            if _class:
                classes.append(_class)
        return ' '.join(classes)

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
            if colname in ('pkey', 'rowidx'):
                continue
            kwargs = dict(selection.colAttrs.get(colname, {}))
            kwargs.pop('tag', None)
            kwargs['name'] = kwargs.pop('label')
            if kwargs['dataType'] == 'D':
                kwargs['format_date'] = 'short'
            size = kwargs.pop('size', None)
            size = kwargs.pop('print_width', size)
            width = self._gridCellWidth(size)
            if width:
                kwargs['width'] = width
            r.child('cell', childname=colname, field=colname, **kwargs)
        return structure

    @staticmethod
    def _gridCellWidth(size: Any) -> Optional[str]:
        """The ``width`` of a grid cell, in ``em``, for a column of *size*.

        The narrower the column the more room it gets per character, from the
        full width below six characters down to 60 % above twenty.  A size
        written ``min:max`` keeps the maximum.

        Args:
            size: The print width or the size of the column, or ``None``.

        Returns:
            The width, or ``None`` when the column declares no size.
        """
        if not size:
            return None
        if isinstance(size, str) and ':' in size:
            size = size.split(':')[1]
        size = int(size)
        if size < 3:
            width = size * 1.1
        elif size < 6:
            width = size
        elif size < 10:
            width = size * .8
        elif size < 20:
            width = size * .7
        else:
            width = size * .6
        return '%iem' % (1 + int(int(width) * .7))

    @public_method
    def getFieldcellPars(self, field: Optional[str] = None,
                         table: Optional[str] = None) -> Bag:
        """Return cell parameters for a field (used by grid column setup).

        Args:
            field: Field path.
            table: Fully qualified table name.

        Returns:
            A :class:`Bag` with cell configuration parameters, plus the
            ``field`` the caller asked for.
        """
        tableobj = self.db.table(table)
        cellpars = cellFromField(field, tableobj,
                                 checkPermissions=self.page.permissionPars)
        cellpars['field'] = field
        return Bag(cellpars)

    # -----------------------------------------------------------------------
    #  File system
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
            columns: Paths to read out of the XML files.
            hierarchical: Return the hierarchical tree rather than
                a flat list.
            applymethod: Post-processing method name.

        Returns:
            The tree :class:`Bag` when *hierarchical*, otherwise the flat Bag
            and the attributes the applymethod added.

        Note:
            Two return types, as in the frozen handler: a Bag on one branch and
            a tuple on the other.
        """
        files = Bag()
        resultAttributes = dict()
        for f in folders.split(','):
            files[f] = StorageResolver(self.page.site.storageNode(f),
                                       include=include, exclude=exclude,
                                       ext=ext, _page=self.page)()
        files.walk(self._fileNodeAttributes(columns), _mode='')
        if hierarchical:
            return files
        result = Bag([('r_%i' % i, None, t[1].attr)
                      for i, t in enumerate(files.getIndex())
                      if t[1].attr and t[1].attr['file_ext'] != 'directory'])
        if applymethod:
            applyPars = self._getApplyMethodPars(kwargs)
            applyresult = self.page.getPublicMethod('rpc', applymethod)(
                result, **applyPars)
            if applyresult:
                resultAttributes.update(applyresult)
        return result, resultAttributes

    def _fileNodeAttributes(self, columns: Optional[str]) -> Callable:
        """The walk callback that turns a storage node into a grid row.

        It gives the node its ``_pkey`` and its two timestamps, both read from
        the modification time because the storage resolver publishes no creation
        time, and reads *columns* out of the file when it is an XML one.

        Args:
            columns: Comma separated Bag paths to read out of an XML file.

        Returns:
            The callback :meth:`gnr.core.gnrbag.Bag.walk` calls per node.
        """
        def setFileAttributes(node: Any, **kwargs: Any) -> None:
            attr = node.attr
            if node.value or not attr:
                return
            abs_path = attr['abs_path']
            attr['_pkey'] = abs_path
            attr['created_ts'] = datetime.fromtimestamp(attr['mtime'])
            attr['changed_ts'] = datetime.fromtimestamp(attr['mtime'])
            if columns and attr['file_ext'].lower() == 'xml':
                with self.page.site.storageNode(abs_path).open('rb') as f:
                    b = Bag(f)
                for c in columns.split(','):
                    attr[c.replace('$', '')] = b[c.replace('$', '')]

        return setFileAttributes

    # -----------------------------------------------------------------------
    #  Relation captions
    # -----------------------------------------------------------------------

    def _relPathToCaption(self, table: str, relpath: str) -> str:
        """Convert a relation path to a human-readable caption.

        Args:
            table: Fully qualified table name.
            relpath: Dot-separated relation path.

        Returns:
            A colon-separated caption string.

        Note:
            Private with an external caller, ``resources/common/th/th_lib.py``,
            so the name stays.
        """
        if not relpath:
            return ''
        tbltree = self.db.relationExplorer(table, dosort=False, pyresolver=True)
        fullcaption = tbltree.cbtraverse(
            relpath, lambda node: self.page._(node.getAttr('name_long')))
        return ':'.join(fullcaption)
