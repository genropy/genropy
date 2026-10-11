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

"""Miscellaneous operations mixin — the copy that receives new work.

Provides :class:`MiscMixin` — a collection of small, autonomous
``@public_method`` endpoints grouped by domain:

- **CRUD**: insert, update, delete, duplicate, archive rows
- **Grid rendering**: transform selections for grid display
- **Frozen selections**: read/check/sum on pickled selections
- **Filesystem**: browse and delete files

The module of the same name under ``gnr.web.gnrwebpage_proxy.apphandler`` is
frozen and is never imported from here.  The method bodies are the ones of
that module; what differs is a block that needs only the table and the
database, replaced by one call on the app level write proxy
``tblobj.writeProxy()``
(:class:`gnr.app.gnrsqltable_proxy.write.WriteProxy`), and a recorded defect
fix, marked in place with its ``bugs_misc.md`` number.

``rpc_getRecordForm`` and ``formAuto`` have no caller anywhere in the tree and
are not part of the copy; ``StorageResolver``, which the frozen module imports
inside ``getFileSystemSelection``, is imported here at module level.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrstring import toText
from gnr.lib.services.storage import StorageResolver
from gnr.web.gnrwebstruct import cellFromField
from gnr.sql.gnrsql_exceptions import GnrSqlDeleteException

__all__ = ['MiscMixin']


class MiscMixin:
    """Mixin for CRUD, grid rendering, frozen selections and utilities.

    Almost every method in this mixin is autonomous.  The exceptions are
    ``_decodeWhereBag`` of the core class, used by ``checkFreezedSelection``,
    ``deleteDbRows``, called by ``saveEditedRows`` because a page may override
    it, and the two blocks more than one method shares:
    ``_checkTableWritePermission`` (``deleteDbRows``, ``duplicateDbRows``) and
    ``_freezedSelection`` (``freezedSelectionPkeys``, ``sumOnFreezedSelection``,
    ``checkFreezedSelection``).
    """

    # -----------------------------------------------------------------------
    #  Blocks more than one method shares
    # -----------------------------------------------------------------------

    def _checkTableWritePermission(self, table: str, permissions: str,
                                   action: str) -> None:
        """Raise the page exception when *table* is closed to *permissions*.

        Called by :meth:`deleteDbRows` and by :meth:`duplicateDbRows`.

        Args:
            table: Fully qualified table name.
            permissions: The comma separated permissions to check.
            action: The word the message opens with, ``Delete`` or
                ``Duplicate``.

        Raises:
            The page ``generic`` exception, when the permission is denied.

        Note:
            bugs_misc.md D4: the two messages of the frozen handler read
            ``'in table % for user %s'``, a float conversion with the space
            flag, so the ``%`` formatting raises ``TypeError`` before the page
            exception is built and every denied call answers the client with
            that ``TypeError``.  There is no legacy message to preserve.
        """
        if self.page.checkTablePermission(table, permissions):
            return
        raise self.page.exception(
            'generic',
            description='%s is not allowed in table %s for user %s' % (action, table, self.user))

    def _freezedSelection(self, table: Optional[str],
                          selectionName: Optional[str]) -> Any:
        """The frozen selection *selectionName* of *table*, or ``None``.

        Called by :meth:`freezedSelectionPkeys`, :meth:`sumOnFreezedSelection`
        and :meth:`checkFreezedSelection`.

        Args:
            table: Fully qualified table name.
            selectionName: Name the selection was frozen under.

        Returns:
            The unpickled selection, or ``None`` when there is no such file.
        """
        return self.page.unfreezeSelection(dbtable=table, name=selectionName)

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
        self.db.table(table).writeProxy().updateCounterField(counterField, changes)

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
        result = Bag()
        wrongUpdates, insertedRecords = self.db.table(table).writeProxy().applyGridChangeset(
            updated=updated, inserted=inserted)
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
            SMELL: ``unlinkfield``, ``commit`` and ``protectPkeys`` are
            accepted but never used — they exist only for signature
            compatibility with ``deleteDbRows``.  The duplication always
            commits (bugs_misc.md B25, reproduced).
        """
        self._checkTableWritePermission(table, 'readonly,ins', 'Duplicate')
        return self.db.table(table).writeProxy().duplicateRecords(pkeys, **kwargs)

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
            The failure branch is unreachable, and would raise if it were
            reached: ``GnrSqlDeleteException`` is imported from the wrong
            module and ``e.message`` does not exist on ``GnrException``.  Both
            are reproduced from the frozen handler (bugs_misc.md D5, D6).
        """
        self._checkTableWritePermission(table, 'readonly,del', 'Delete')
        try:
            writer = self.db.table(table).writeProxy()
            rows = writer.fetchRowsToDelete(pkeys)
            if not rows:
                return
            labelfield = writer.chooseDeleteLabelField(rows)
            deltitle = 'Unlink records' if unlinkfield else 'Delete records'
            writer.deleteRows(self.page.utils.quickThermo(rows, maxidx=len(rows),
                                                          labelfield=labelfield, title=deltitle),
                              unlinkfield=unlinkfield, protectPkeys=protectPkeys, commit=commit)
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
            self.db.table(table).writeProxy().archiveRows(pkeys, archiveDate=archiveDate,
                                                            protectPkeys=protectPkeys,
                                                            commit=commit)
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

        Note:
            The raw items of the client record are re-applied over what
            ``newrecord`` computed, so a sysfield or a unique column the client
            sent wins over the table (bugs_misc.md A3, reproduced).
        """
        return self.db.table(table).writeProxy().insertRecord(record)

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
        return self.db.table(table).writeProxy().duplicateRecord(pkey, **kwargs)

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
        self.db.table(table).writeProxy().unifyRecords(sourcePkey, destPkey)

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
            Every field of the payload is written, a ``None`` included; the
            insert branch of ``saveRecord`` drops it instead (bugs_misc.md
            A13 vs A9, both reproduced).
        """
        self.db.table(table).writeProxy().updateRecord(pkey, record)

    @public_method
    def saveRecord(self, table=None, pkey=None, data=None, **kwargs):
        """Insert or update the record a form sent, and return its pkey.

        Note:
            bugs_misc.md D7: the frozen handler returns the pkey the **client**
            sent, so a new record comes back as ``{'pkey': None}`` from a Bag
            payload and raises ``KeyError`` from a plain dict, and the form
            keeps ``*newrecord*`` as its current pkey.  Here the insert branch
            returns the pkey the insert wrote.
        """
        return dict(pkey=self.db.table(table).writeProxy().saveRecord(pkey, data))

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
        self.db.table(table).writeProxy().touchRecords(pkeys)

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
        fields = changesDict.pop('_fields', None)
        self.db.table(table).writeProxy().updateCheckboxRecords(field, changesDict, fields=fields)

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
            attributes = selection.typedAttributes(kw.get('_attributes'))
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
                    elif size < 6:  # bugs_misc.md D8: the frozen handler is missing the ``elif``
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

        Note:
            bugs_misc.md D9: the frozen handler reads the caption under the
            literal key ``'caption_field'``, so the parameter is only a
            truthiness switch and every real column name raises ``KeyError``.
        """
        selection = self._freezedSelection(table, selectionName)
        l = selection.output('dictlist')
        return [dict(pkey=r['pkey'], caption=r[caption_field]) if caption_field else r['pkey'] for r in l]

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
            The list ``selection.sum`` returns, one item per column, or the
            integer ``0`` if the selection is missing.
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
