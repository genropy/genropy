# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy app - see LICENSE for details
# module gnrsqltable_proxy.write : table level part of the record write flows
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

"""Table level part of the record write flows of the application handler.

:class:`WriteProxy` is attached to every table of a ``GnrApp`` database by
``gnr.app.gnrdbo.TableBase.writeProxy``.  It is the third table proxy, next to
:class:`gnr.app.gnrsqltable_proxy.selection.SelectionProxy`, which serves the
getSelection flow, and :class:`gnr.app.gnrsqltable_proxy.record.RecordProxy`,
which serves the read side of the record flows.  This one holds the write side:
insert, update, duplicate, unify, delete, archive, and the two batch updates the
grid sends.

It never references a web page.  The permission checks, the progress thermo and
the deletion hook a page may override stay on the handler; what arrives here is
the data and, where a page service drives a loop, the iterable the handler
already built.

Every method takes a ``commit`` flag and commits through ``self.db``, so the
caller never has to commit behind the proxy's back.  The flag default is what
the handler method it serves does today.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from gnr.core.gnrbag import Bag


class WriteProxy:
    """Write proxy of a single table."""

    def __init__(self, tblobj: Any) -> None:
        self.tblobj = tblobj

    @property
    def db(self) -> Any:
        """The database of the proxied table."""
        return self.tblobj.db

    def _commit(self, commit: bool) -> None:
        """Commit when *commit* asks for it."""
        if commit:
            self.db.commit()

    # ------------------------------------------------------------------
    #  One record at a time
    # ------------------------------------------------------------------

    def insertRecord(self, record: Any, commit: bool = True) -> str:
        """Insert *record* and return the pkey the insert produced.

        The record is built by ``newrecord``, which drops the sysfields, the
        unique columns and the empty values of *record* and adds the table
        defaults; the values of *record* are then re-applied over the result, so
        what the caller sent wins over what the table computed.

        Args:
            record: the record the caller sent, a Bag or a dict.
            commit: commit after the insert.

        Returns:
            The pkey of the inserted record.
        """
        tblobj = self.tblobj
        newrecord = tblobj.newrecord(_fromRecord=record)
        newrecord.update({k: v for k, v in record.items()})
        tblobj.insert(newrecord)
        self._commit(commit)
        return newrecord[tblobj.pkey]

    def updateRecord(self, pkey: str, record: Any, commit: bool = True) -> None:
        """Write every item of *record* into the record *pkey*; returns nothing.

        A value of ``None`` is written, unlike the insert branch of
        :meth:`saveRecord`.

        Args:
            pkey: the pkey of the record to update.
            record: the fields to write, a Bag or a dict.
            commit: commit after the update.
        """
        with self.tblobj.recordToUpdate(pkey) as recToUpd:
            for k, v in record.items():
                recToUpd[k] = v
        self._commit(commit)

    def saveRecord(self, pkey: Optional[str], data: Any,
                   commit: bool = True) -> Optional[str]:
        """Insert or update the record the form sent, and return the pkey of what was saved.

        The literal ``'*newrecord*'`` selects the insert branch, which is the
        pkey the client sends for a record that does not exist yet.  On that
        branch the empty values are dropped and the pkey is the one the insert
        produced; on the update branch every value is written, and the pkey is
        the one *data* carries, which is how a form renames a record.

        Args:
            pkey: the pkey of the record, or ``'*newrecord*'``.
            data: the fields the form sent.
            commit: commit after the write.

        Returns:
            The pkey of the saved record.
        """
        tblobj = self.tblobj
        if pkey == '*newrecord*':
            newrecord = tblobj.newrecord(
                **{k: v for k, v in data.items() if v is not None})
            tblobj.insert(newrecord)
            saved_pkey = newrecord[tblobj.pkey]
        else:
            with tblobj.recordToUpdate(pkey) as recToUpd:
                for k, v in data.items():
                    recToUpd[k] = v
            saved_pkey = data[tblobj.pkey]
        self._commit(commit)
        return saved_pkey

    def duplicateRecord(self, pkey: str, commit: bool = True,
                        **kwargs: Any) -> str:
        """Duplicate the record *pkey* and return the pkey of the copy.

        Args:
            pkey: the pkey of the record to duplicate.
            commit: commit after the insert.
            kwargs: forwarded to ``tblobj.duplicateRecord``.

        Returns:
            The pkey of the new record.
        """
        record = self.tblobj.duplicateRecord(pkey, **kwargs)
        self._commit(commit)
        return record[self.tblobj.pkey]

    def duplicateRecords(self, pkeys: Iterable[str], commit: bool = True,
                         **kwargs: Any) -> list:
        """Duplicate every pkey of *pkeys* and return the new pkeys.

        Args:
            pkeys: the pkeys to duplicate.
            commit: commit once, after the last insert.
            kwargs: forwarded to ``tblobj.duplicateRecord``.

        Returns:
            The pkeys of the new records, in the order of *pkeys*.
        """
        tblobj = self.tblobj
        result = [tblobj.duplicateRecord(pkey, **kwargs)[tblobj.pkey]
                  for pkey in pkeys]
        self._commit(commit)
        return result

    def unifyRecords(self, sourcePkey: str, destPkey: str,
                     commit: bool = True) -> None:
        """Merge the record *sourcePkey* into *destPkey*; returns nothing.

        Args:
            sourcePkey: the record that is merged away.
            destPkey: the record that survives.
            commit: commit after the merge.
        """
        self.tblobj.unifyRecords(sourcePkey=sourcePkey, destPkey=destPkey)
        self._commit(commit)

    # ------------------------------------------------------------------
    #  Batch updates
    # ------------------------------------------------------------------

    def updateCounterField(self, counterField: str, changes: Iterable[dict],
                           commit: bool = True) -> None:
        """Write the new counter values *changes* carries into *counterField*; returns nothing.

        The update is raw — the triggers do not run — unless the counter column
        declares ``triggerOnUpdate``.  The draft rows are updated too.

        Args:
            counterField: the counter column to write.
            changes: dicts with a ``_pkey`` and a ``new`` key.
            commit: commit after the batch.
        """
        tblobj = self.tblobj
        updaterDict = {d['_pkey']: d['new'] for d in changes}

        def cb(row: dict) -> None:
            row[counterField] = updaterDict[row[tblobj.pkey]]

        raw_update = not tblobj.column(counterField).attributes.get(
            'triggerOnUpdate')
        tblobj.batchUpdate(cb, where='$%s IN:pkeys' % tblobj.pkey,
                           pkeys=list(updaterDict.keys()),
                           excludeDraft=False, _raw_update=raw_update)
        self._commit(commit)

    def touchRecords(self, pkeys: Iterable[str], commit: bool = True) -> None:
        """Run the update triggers on the records *pkeys* with no user change; returns nothing.

        Args:
            pkeys: the pkeys to touch.
            commit: commit after the touch.
        """
        self.tblobj.touchRecords(_pkeys=pkeys)
        self._commit(commit)

    def updateCheckboxRecords(self, field: str, changesDict: dict,
                              fields: Optional[list] = None,
                              commit: bool = True) -> None:
        """Write the checkbox values *changesDict* carries into the records; returns nothing.

        When *fields* names more than one column the semantic is a radio group:
        *field* takes the value the caller sent and every other column of
        *fields* is set to ``False``.  A draft row is not updated, because
        ``batchUpdate`` excludes the drafts by default.

        Args:
            field: the column the caller toggled.
            changesDict: the new value per pkey.
            fields: the columns of the group; *field* alone when it is empty.
            commit: commit after the batch.
        """
        tblobj = self.tblobj
        fields = fields or [field]

        def cb(row: dict) -> None:
            for f in fields:
                row[f] = changesDict[row[tblobj.pkey]] if f == field else False

        tblobj.batchUpdate(cb, where='$%s IN :pkeys' % tblobj.pkey,
                           pkeys=list(changesDict.keys()))
        self._commit(commit)

    def applyGridChangeset(self, updated: Optional[dict] = None,
                           inserted: Optional[Any] = None) -> tuple[Bag, Bag]:
        """Apply the updates and the inserts of a grid changeset and return the refused rows and the inserted pkeys.

        A field carrying a ``_loadedValue`` that no longer matches the value in
        the database abandons the **whole** row: the row is recorded in the
        returned ``wrongUpdates`` and the fields after it are not applied
        either.  A field absent from the row but carrying a ``_loadedValue`` is
        written all the same.  Nothing is committed here, because the caller
        still has the deletions to run.

        Args:
            updated: ``{pkey: Bag of fields}``, as the changeset digests it.
            inserted: the rows to insert, keyed the way the changeset keys them.

        Returns:
            ``(wrongUpdates, insertedRecords)``: the rows a concurrent edit
            stopped, and the pkey of every inserted row under the key the
            changeset used.
        """
        tblobj = self.tblobj
        pkeyfield = tblobj.pkey
        wrongUpdates = Bag()
        insertedRecords = Bag()

        def cb(row: dict) -> None:
            fields = updated.get(row[pkeyfield])
            if not fields:
                return
            for node in fields:
                if node.label not in row:
                    if '_loadedValue' in node.attr:
                        row[node.label] = node.value
                    continue
                if isinstance(node.value, Bag):
                    node.value.popAttributesFromNodes(
                        ['_loadedValue', 'dtype', '__old'])
                elif ('_loadedValue' in node.attr
                        and row[node.label] != node.attr['_loadedValue']):
                    wrongUpdates[row[pkeyfield]] = row
                    return
                row[node.label] = node.value

        if updated:
            tblobj.batchUpdate(cb, _pkeys=[p for p in updated.keys() if p],
                               bagFields=True)
        if inserted:
            for key, row in list(inserted.items()):
                tblobj.insert(row)
                insertedRecords[key] = row[pkeyfield]
        return wrongUpdates, insertedRecords

    # ------------------------------------------------------------------
    #  Deleting and archiving
    # ------------------------------------------------------------------

    def fetchRowsToDelete(self, pkeys: Iterable[str],
                          subtable: Optional[str] = '*') -> list:
        """Return the rows *pkeys* names, fetched and locked, drafts and deleted ones included.

        Args:
            pkeys: the pkeys to fetch.
            subtable: the subtable selector, ``'*'`` for the delete flow and
                ``None`` for the archive one, which does not ask for it.

        Returns:
            The locked rows.
        """
        kwargs = dict(subtable=subtable) if subtable else {}
        return self.tblobj.query(where='$%s IN :pkeys' % self.tblobj.pkey,
                                 pkeys=pkeys, excludeLogicalDeleted=False,
                                 for_update=True, addPkeyColumn=False,
                                 excludeDraft=False, **kwargs).fetch()

    def chooseDeleteLabelField(self, rows: list) -> str:
        """Return the column the progress bar shows while *rows* are deleted.

        The caption field of the table when the fetched rows carry it, the table
        name otherwise.

        Args:
            rows: the fetched rows.

        Returns:
            A column name, or the table name when no caption column was fetched.
        """
        caption_field = self.tblobj.attributes.get('caption_field')
        if caption_field and rows and caption_field in rows[0]:
            return caption_field
        return self.tblobj.name

    def deleteRows(self, rows: Iterable[dict], unlinkfield: Optional[str] = None,
                   protectPkeys: Optional[Iterable[str]] = None,
                   commit: bool = True) -> None:
        """Delete, unlink or logically delete every row of *rows*; returns nothing.

        With *unlinkfield* the row is kept and the field set to ``None``.  A
        pkey listed in *protectPkeys* is logically deleted instead of deleted,
        which needs a table with a logical deletion field: without one the list
        has no effect.  *rows* is iterated as it arrives, so the caller may wrap
        it in a progress bar.

        Args:
            rows: the rows to delete, already fetched and locked.
            unlinkfield: the field to null out instead of deleting.
            protectPkeys: the pkeys to logically delete.
            commit: commit after the last row.
        """
        tblobj = self.tblobj
        logicalDeletionField = tblobj.logicalDeletionField
        now = datetime.now()
        for row in rows:
            if unlinkfield:
                unlinked = dict(row)
                unlinked[unlinkfield] = None
                tblobj.update(unlinked, row)
            elif (protectPkeys and logicalDeletionField
                    and row[tblobj.pkey] in protectPkeys):
                oldrow = dict(row)
                row[logicalDeletionField] = now
                tblobj.update(row, oldrow)
            else:
                tblobj.delete(row)
        self._commit(commit)

    def archiveRows(self, pkeys: Iterable[str], archiveDate: Any = None,
                    protectPkeys: Optional[Iterable[str]] = None,
                    commit: bool = True) -> None:
        """Write *archiveDate* into the logical deletion field of *pkeys*; returns nothing.

        An *archiveDate* of ``None`` writes ``None``, which un-archives the
        rows.  A pkey listed in *protectPkeys* is left alone — the opposite of
        what the same parameter means in :meth:`deleteRows`.  Nothing is
        committed when no row changed.

        Args:
            pkeys: the pkeys to archive.
            archiveDate: the date to write, truncated to midnight.
            protectPkeys: the pkeys to leave alone.
            commit: commit after the last row, when at least one changed.
        """
        tblobj = self.tblobj
        ts = datetime(archiveDate.year, archiveDate.month,
                      archiveDate.day) if archiveDate else None
        protectPkeys = protectPkeys or []
        updated = False
        for row in self.fetchRowsToDelete(pkeys, subtable=None):
            if row[tblobj.pkey] in protectPkeys:
                continue
            oldrow = dict(row)
            row[tblobj.logicalDeletionField] = ts
            tblobj.update(row, oldrow)
            updated = True
        self._commit(commit and updated)
