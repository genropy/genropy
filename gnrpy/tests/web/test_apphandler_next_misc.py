"""Equivalence between the misc flows of the two handlers.

``GnrWebAppHandlerNext`` moves the table level part of the record writes and of
the row operations onto an app level table proxy (``tblobj.writeHandler()``) and
decomposes the rest — frozen selections, grid rendering, file system — into
helpers on the handler.  It is a refactoring, so the same input must leave the
same rows in the database and give the same result through both handlers; the
declared divergences are the defect fixes of ``bugs_misc.md`` and each of them
has a test that asserts the divergence instead of the equality.

Every case covers one row of the behaviour tables in
``.subtasks/alt-apphandler/progress_misc.md``, named in its docstring.

The writes go through the real ``test_invoice`` database.  A write is not
idempotent, so a case that compares the two handlers gives each of them its own
row, after making the two rows identical, and compares what the database holds
afterwards.  ``invc.invoice_note`` is the table of choice because its rows are
independent of each other and it has no triggers; ``invc.invoice_row`` is
unusable, because ``calculateTotals`` of the test project adds a ``Decimal`` to
a ``float`` and raises on every update.
"""

import datetime

import pytest

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from gnr.sql.gnrsqltable import GnrSqlDeleteException as TableDeleteException
from gnr.sql.gnrsql_exceptions import GnrSqlDeleteException as ImportedDeleteException

# pytest resolves fixtures by name in the module namespace, so the shared ones
# are imported even though nothing in this file calls them.
from apphandler_next_common import (gnr_test_config, db,  # noqa: F401
                                    make_handlers, handlers, storage_handlers)


NOTE_TABLE = 'invc.invoice_note'
NOTE_COLUMNS = '$invoice_id,$note_type,$note_text,$priority,$__del_ts'


# ---------------------------------------------------------------------------
#  Rows to write on
# ---------------------------------------------------------------------------

class _PkeyPool:
    """Hands out pkeys nobody has written on yet.

    The cases of this module change the rows they touch and the database lives
    for the whole module, so every case asks the pool for its own rows instead
    of picking the first ones it finds.
    """

    def __init__(self, pkeys):
        self.pkeys = pkeys
        self.used = 0

    def take(self, howmany=1):
        """The next *howmany* pkeys, never handed out before."""
        assert self.used + howmany <= len(self.pkeys), 'the pkey pool is empty'
        taken = self.pkeys[self.used:self.used + howmany]
        self.used += howmany
        return taken


@pytest.fixture(scope='module')
def notes(db):  # noqa: F811
    """A pool over the 387 rows of invc.invoice_note."""
    rows = db.table(NOTE_TABLE).query(columns='$id', order_by='$id').fetch()
    return _PkeyPool([r['id'] for r in rows])


@pytest.fixture(scope='module')
def customers(db):  # noqa: F811
    """A pool over the rows of invc.customer, which has a draft field."""
    rows = db.table('invc.customer').query(columns='$id', order_by='$id',
                                           limit=200).fetch()
    return _PkeyPool([r['id'] for r in rows])


@pytest.fixture(scope='module')
def an_invoice(db):  # noqa: F811
    """The pkey of one invoice, for the notes the cases insert."""
    return db.table('invc.invoice').query(columns='$id', limit=1).fetch()[0]['id']


def note_row(db, pkey):
    """The comparable content of one invoice_note row, or ``None``."""
    rows = db.table(NOTE_TABLE).query(columns=NOTE_COLUMNS, where='$id=:p',
                                      p=pkey, excludeLogicalDeleted=False,
                                      excludeDraft=False).fetch()
    if not rows:
        return None
    row = dict(rows[0])
    row.pop('pkey', None)
    return row


def twin_notes(db, notes, an_invoice, **values):
    """Two invoice_note rows with the same content, one per handler.

    Every comparable column is written, not only the ones the case cares about,
    so that what the two rows hold afterwards differs only by what the handlers
    did to them.

    Args:
        db: the database.
        notes: the pkey pool.
        an_invoice: the invoice both rows belong to.
        values: the columns the case wants, over the common baseline.

    Returns:
        The two pkeys, in the order legacy, next.
    """
    baseline = dict(invoice_id=an_invoice, note_type='TWIN', note_text='twin',
                    priority=0, __del_ts=None)
    baseline.update(values)
    pkeys = notes.take(2)
    tblobj = db.table(NOTE_TABLE)
    for pkey in pkeys:
        with tblobj.recordToUpdate(pkey) as record:
            for k, v in baseline.items():
                record[k] = v
    db.commit()
    assert note_row(db, pkeys[0]) == note_row(db, pkeys[1])
    return pkeys


def assert_twins_agree(db, pkeys):
    """The two rows the two handlers wrote hold the same thing."""
    assert note_row(db, pkeys[0]) == note_row(db, pkeys[1])


# ---------------------------------------------------------------------------
#  Flow A — record writes
# ---------------------------------------------------------------------------

def test_insert_record(handlers, db, an_invoice):  # noqa: F811
    """A1-A6: the same record Bag gives the same row through both handlers."""
    written = []
    for handler in handlers:
        record = Bag(dict(invoice_id=an_invoice, note_type='INS',
                          note_text='inserted', priority=4))
        pkey = handler.insertRecord(table=NOTE_TABLE, record=record)
        assert pkey, 'insertRecord must return the pkey the insert produced'
        written.append(note_row(db, pkey))
    assert written[0] == written[1]
    assert written[0]['note_text'] == 'inserted'


def test_insert_record_client_values_win_over_the_defaults(handlers, db):  # noqa: F811
    """A3: a unique column recordCopy drops is re-applied by the raw update.

    ``invc.invoice.inv_number`` is unique and carries a counter, so
    ``newrecord`` leaves it to ``setRowCounter``; the re-apply of the client
    values puts the one the client sent back on top of it.
    """
    customer = db.table('invc.customer').query(columns='$id', limit=1).fetch()[0]
    numbers = []
    for i, handler in enumerate(handlers):
        record = Bag(dict(inv_number='PHASE5-%i' % i, customer_id=customer['id'],
                          date=datetime.date(2026, 3, 3)))
        pkey = handler.insertRecord(table='invc.invoice', record=record)
        numbers.append(db.table('invc.invoice').record(pkey).output('dict')['inv_number'])
    assert numbers == ['PHASE5-0', 'PHASE5-1']


def test_update_record(handlers, db, notes, an_invoice):  # noqa: F811
    """A8-A10: the same fields are written on the record of each handler."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='before', priority=1)
    for handler, pkey in zip(handlers, pkeys):
        handler.updateRecord(table=NOTE_TABLE, pkey=pkey,
                             record=Bag(dict(note_text='after', priority=9)))
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['note_text'] == 'after'


def test_update_record_writes_the_empty_values(handlers, db, notes, an_invoice):  # noqa: F811
    """A9: a None in the record reaches the column, unlike on a save insert."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='filled')
    for handler, pkey in zip(handlers, pkeys):
        handler.updateRecord(table=NOTE_TABLE, pkey=pkey,
                             record=Bag(dict(note_text=None)))
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['note_text'] is None


def test_save_record_new_returns_the_inserted_pkey_only_in_next(handlers, db, an_invoice):  # noqa: F811,E501
    """A16, defect D7: the frozen handler returns the pkey the client sent.

    Both handlers insert the row; only the copy tells the caller where it is.
    ``genro_frm.js:2861`` falls back to the current pkey when the answer has
    none, so the form of the frozen handler keeps ``*newrecord*``.
    """
    legacy, nxt = handlers
    results = []
    for handler in (legacy, nxt):
        data = Bag(dict(invoice_id=an_invoice, note_type='SAVE',
                        note_text='saved', priority=2))
        results.append(handler.saveRecord(table=NOTE_TABLE, pkey='*newrecord*',
                                          data=data))
    assert results[0] == dict(pkey=None)
    assert results[1]['pkey']
    assert note_row(db, results[1]['pkey'])['note_text'] == 'saved'
    inserted = db.table(NOTE_TABLE).query(columns='$id', where='$note_text=:t',
                                          t='saved').fetch()
    assert len(inserted) == 2, 'both handlers must insert the row'


def test_save_record_new_drops_the_empty_values(handlers, db, an_invoice):  # noqa: F811
    """A13: a None in the payload does not reach the insert."""
    for handler in handlers:
        data = Bag(dict(invoice_id=an_invoice, note_type='DROP',
                        note_text='kept', priority=None))
        handler.saveRecord(table=NOTE_TABLE, pkey='*newrecord*', data=data)
    rows = db.table(NOTE_TABLE).query(columns=NOTE_COLUMNS, where='$note_type=:t',
                                      t='DROP').fetch()
    assert len(rows) == 2
    assert [r['priority'] for r in rows] == [None, None]


def test_save_record_update_writes_the_empty_values(handlers, db, notes, an_invoice):  # noqa: F811
    """A14, A16: the update branch writes the Nones and returns the data pkey."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='filled', priority=5)
    tblobj = db.table(NOTE_TABLE)
    for handler, pkey in zip(handlers, pkeys):
        data = Bag(dict(priority=None))
        data[tblobj.pkey] = pkey
        assert handler.saveRecord(table=NOTE_TABLE, pkey=pkey, data=data) == dict(pkey=pkey)
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['priority'] is None


def test_duplicate_record(handlers, db, notes, an_invoice):  # noqa: F811
    """A18-A20: the copy of the same row holds the same content."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='original', priority=3)
    copies = []
    for handler, pkey in zip(handlers, pkeys):
        newpkey = handler.duplicateRecord(table=NOTE_TABLE, pkey=pkey)
        assert newpkey != pkey
        copies.append(note_row(db, newpkey))
    assert copies[0] == copies[1]
    assert copies[0]['note_text'] == 'original'


def test_unify_records(handlers, db, notes):  # noqa: F811
    """A22-A23: the source disappears and the destination survives."""
    for handler in handlers:
        source, dest = notes.take(2)
        handler.unifyRecords(table=NOTE_TABLE, sourcePkey=source, destPkey=dest)
        assert note_row(db, source) is None
        assert note_row(db, dest) is not None


def test_new_rows_data(handlers, db):  # noqa: F811
    """A37-A41: the defaults fill the None values and the keys are positional."""
    rows = [dict(inv_number='N1'), dict(inv_number='', total=0, date=None)]
    results = [handler.newRowsData(table='invc.invoice', rows=list(rows))
               for handler in handlers]
    assert results[0].asDict(ascii=True) == results[1].asDict(ascii=True)
    assert [node.label for node in results[0]] == ['r_0', 'r_1']
    assert results[0]['r_0.date'] == db.workdate
    assert results[0]['r_1.inv_number'] == ''
    assert results[0]['r_1.total'] == 0


def test_counter_field_changes(handlers, db, an_invoice):  # noqa: F811
    """A42-A46: the counter column takes the values the changes carry."""
    tblobj = db.table('invc.invoice_row')
    rows = tblobj.query(columns='$id,$_row_count', where='$invoice_id=:i',
                        i=an_invoice, order_by='$id').fetch()
    assert len(rows) >= 2, 'the invoice must have rows to renumber'
    for offset, (handler, row) in enumerate(zip(handlers, rows)):
        changes = [dict(_pkey=row['id'], new=90 + offset)]
        handler.counterFieldChanges(table='invc.invoice_row',
                                    counterField='_row_count', changes=changes)
    after = tblobj.query(columns='$id,$_row_count',
                         where='$id IN :p', p=[r['id'] for r in rows[:2]],
                         order_by='$_row_count').fetch()
    assert [r['_row_count'] for r in after] == [90, 91]


# ---------------------------------------------------------------------------
#  Flow A — saveEditedRows
# ---------------------------------------------------------------------------

def updated_changeset(rows):
    """A grid changeset with an ``updated`` sub-bag.

    Args:
        rows: ``(pkey, {field: value}, {field: loaded value})`` per row.

    Returns:
        The changeset Bag the client sends.
    """
    changeset = Bag()
    updated = Bag()
    for i, (pkey, fields, loaded) in enumerate(rows):
        row = Bag()
        for k, v in fields.items():
            if k in loaded:
                row.setItem(k, v, _loadedValue=loaded[k])
            else:
                row.setItem(k, v)
        updated.setItem('r_%i' % i, row, _pkey=pkey)
    changeset['updated'] = updated
    return changeset


def test_save_edited_rows_updates(handlers, db, notes, an_invoice):  # noqa: F811
    """A27-A32, A35-A36: the edited fields land in the database."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='before', priority=1)
    for handler, pkey in zip(handlers, pkeys):
        changeset = updated_changeset([
            (pkey, dict(note_text='edited', priority=8),
             dict(note_text='before'))])
        result = handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset)
        assert len(result['wrongUpdates']) == 0
        assert len(result['insertedRecords']) == 0
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['note_text'] == 'edited'


def test_save_edited_rows_conflict_abandons_the_whole_row(handlers, db, notes, an_invoice):  # noqa: F811
    """A30: a stale _loadedValue stops the row, and the later fields too."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='current', priority=1)
    for handler, pkey in zip(handlers, pkeys):
        changeset = updated_changeset([
            (pkey, dict(note_text='edited', priority=8),
             dict(note_text='stale'))])
        result = handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset)
        assert list(result['wrongUpdates'].keys()) == [pkey]
    assert_twins_agree(db, pkeys)
    row = note_row(db, pkeys[0])
    assert row['note_text'] == 'current'
    assert row['priority'] == 1, 'the field after the conflict must not be written'


def test_save_edited_rows_writes_a_field_absent_from_the_row(handlers, db, notes, an_invoice):  # noqa: F811
    """A31: a field the fetched row does not carry is written all the same.

    ``batchUpdate`` fetches the columns the table has, so the case needs a name
    that is not one of them: the value lands in the row dict and the update
    ignores it, which is what both handlers do, identically.
    """
    pkeys = twin_notes(db, notes, an_invoice, note_text='untouched')
    for handler, pkey in zip(handlers, pkeys):
        changeset = updated_changeset([
            (pkey, dict(not_a_column='x'), dict(not_a_column=None))])
        handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset)
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['note_text'] == 'untouched'


def test_save_edited_rows_inserts_and_deletes(handlers, db, notes, an_invoice):  # noqa: F811
    """A33-A34: the inserted rows come back with their pkey, the deleted go."""
    for handler in handlers:
        victim = notes.take(1)[0]
        changeset = Bag()
        changeset['inserted'] = Bag([('n0', dict(invoice_id=an_invoice,
                                                 note_type='GRID',
                                                 note_text='from the grid',
                                                 priority=6))])
        changeset.setItem('deleted', Bag([('d0', None, dict(_pkey=victim))]))
        result = handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset)
        newpkey = result['insertedRecords']['n0']
        assert note_row(db, newpkey)['note_text'] == 'from the grid'
        assert note_row(db, victim) is None


def test_save_edited_rows_empties_the_changeset(handlers, db, notes):  # noqa: F811
    """A26: the three sub-bags are popped out of the caller's Bag."""
    for handler in handlers:
        pkey = notes.take(1)[0]
        changeset = updated_changeset([(pkey, dict(note_text='x'), {})])
        handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset)
        assert len(changeset) == 0


def test_save_edited_rows_without_changeset_returns_none(handlers):
    """A25: an empty changeset returns None, not a Bag."""
    for handler in handlers:
        assert handler.saveEditedRows(table=NOTE_TABLE, changeset=None) is None
        assert handler.saveEditedRows(table=NOTE_TABLE, changeset=Bag()) is None


def test_save_edited_rows_without_commit(handlers, db, notes, an_invoice):  # noqa: F811
    """A35: with commit False the change is in the transaction, not committed."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='before')
    for handler, pkey in zip(handlers, pkeys):
        changeset = updated_changeset([(pkey, dict(note_text='uncommitted'), {})])
        handler.saveEditedRows(table=NOTE_TABLE, changeset=changeset, commit=False)
        assert note_row(db, pkey)['note_text'] == 'uncommitted'
        db.rollback()
        assert note_row(db, pkey)['note_text'] == 'before'


# ---------------------------------------------------------------------------
#  Flow B — row operations
# ---------------------------------------------------------------------------

def test_delete_db_rows(handlers, db, notes, an_invoice):  # noqa: F811
    """B3, B10, B11: the rows are gone on both sides."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        assert handler.deleteDbRows(NOTE_TABLE, pkeys=[pkey]) is None
        assert note_row(db, pkey) is None


def test_delete_db_rows_unlink(handlers, db, notes, an_invoice):  # noqa: F811
    """B8: with an unlinkfield the row survives with that field emptied."""
    pkeys = twin_notes(db, notes, an_invoice, note_type='LINKED')
    for handler, pkey in zip(handlers, pkeys):
        handler.deleteDbRows(NOTE_TABLE, pkeys=[pkey], unlinkfield='note_type')
    assert_twins_agree(db, pkeys)
    row = note_row(db, pkeys[0])
    assert row is not None
    assert row['note_type'] is None


def test_delete_db_rows_protected_is_logically_deleted(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """B9: a protected pkey gets the deletion timestamp instead of a DELETE."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        handler.deleteDbRows(NOTE_TABLE, pkeys=[pkey], protectPkeys=[pkey])
    rows = [note_row(db, pkey) for pkey in pkeys]
    assert all(row is not None and row['__del_ts'] is not None for row in rows)


def test_delete_db_rows_without_rows_returns_none(handlers, db):  # noqa: F811
    """B5: an unknown pkey returns before the commit, with no error."""
    for handler in handlers:
        assert handler.deleteDbRows(NOTE_TABLE, pkeys=['no-such-pkey']) is None


def test_delete_db_rows_drives_the_same_thermo(handlers, db, notes, an_invoice):  # noqa: F811
    """B4, B6, B7: same title, same label field, same row count."""
    pkeys = twin_notes(db, notes, an_invoice)
    calls = []
    for handler, pkey in zip(handlers, pkeys):
        handler.page.utils.thermo_calls.clear()
        handler.deleteDbRows(NOTE_TABLE, pkeys=[pkey])
        calls.append(handler.page.utils.thermo_calls)
    assert calls[0] == calls[1]
    assert calls[0] == [dict(maxidx=1, labelfield='invoice_note',
                             title='Delete records', rowcount=1)]


def test_delete_db_rows_thermo_title_says_unlink(handlers, db, notes, an_invoice):  # noqa: F811
    """B6: the title is the other literal when the operation is an unlink."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        handler.page.utils.thermo_calls.clear()
        handler.deleteDbRows(NOTE_TABLE, pkeys=[pkey], unlinkfield='note_type')
        assert handler.page.utils.thermo_calls[0]['title'] == 'Unlink records'


def test_delete_db_rows_uses_the_caption_field_as_label(handlers, db):  # noqa: F811
    """B4: a table with a caption field among the fetched columns uses it.

    ``invc.invoice_note`` has none, so the label falls back to the table name;
    ``invc.customer`` has ``account_name``, and a customer with no invoices can
    be deleted without tripping the ``onDelete='raise'`` of the invoices.
    """
    victims = db.table('invc.customer').query(
        columns='$id', where='$n_invoices=0 OR $n_invoices IS NULL',
        limit=2).fetch()
    assert len(victims) == 2, 'two customers with no invoice are needed'
    for handler, victim in zip(handlers, victims):
        handler.page.utils.thermo_calls.clear()
        assert handler.deleteDbRows('invc.customer', pkeys=[victim['id']]) is None
        assert handler.page.utils.thermo_calls[0]['labelfield'] == 'account_name'


def test_delete_db_rows_permission_denied_diverges(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """B2, defect D4: the frozen handler raises TypeError, the copy the error.

    ``'in table % for user %s'`` is a float conversion with the space flag, so
    the message formatting blows up before ``page.exception`` is built and the
    caller never sees the permission error.
    """
    legacy, nxt = handlers
    pkey = notes.take(1)[0]
    for handler in handlers:
        handler.page.forbidden_permissions = {'del'}
    try:
        with pytest.raises(TypeError) as legacy_error:
            legacy.deleteDbRows(NOTE_TABLE, pkeys=[pkey])
        assert 'must be real number' in str(legacy_error.value)
        with pytest.raises(GnrException) as next_error:
            nxt.deleteDbRows(NOTE_TABLE, pkeys=[pkey])
        assert NOTE_TABLE in next_error.value.description
        assert 'admin' in next_error.value.description
    finally:
        for handler in handlers:
            handler.page.forbidden_permissions = set()
    assert note_row(db, pkey) is not None, 'neither handler may delete the row'


def test_duplicate_db_rows_permission_denied_diverges(handlers, db, notes):  # noqa: F811
    """B23, defect D4: the same divergence on the duplication permission."""
    legacy, nxt = handlers
    pkey = notes.take(1)[0]
    for handler in handlers:
        handler.page.forbidden_permissions = {'ins'}
    try:
        with pytest.raises(TypeError):
            legacy.duplicateDbRows(NOTE_TABLE, pkeys=[pkey])
        with pytest.raises(GnrException) as next_error:
            nxt.duplicateDbRows(NOTE_TABLE, pkeys=[pkey])
        assert next_error.value.description.startswith('Duplicate is not allowed')
    finally:
        for handler in handlers:
            handler.page.forbidden_permissions = set()


def test_delete_exception_escapes_both_handlers(handlers, db):  # noqa: F811
    """B12, defects D5 and D6: the except clause cannot fire, in either handler.

    ``invc.customer`` declares ``onDelete='raise'`` on its invoices, so deleting
    a customer that has some raises through ``EXCEPTIONS['delete']``, which is
    ``gnr.sql.gnrsqltable.GnrSqlDeleteException`` — not the homonym of
    ``gnr.sql.gnrsql_exceptions`` the two modules import.  The tuple
    ``('delete_error', ...)`` is unreachable, and ``e.message`` would raise if
    it were reached.
    """
    assert ImportedDeleteException is not TableDeleteException
    assert not hasattr(TableDeleteException(description='x'), 'message')
    victim = db.table('invc.customer').query(columns='$id', where='$n_invoices>0',
                                             limit=1).fetch()[0]['id']
    for handler in handlers:
        with pytest.raises(TableDeleteException):
            handler.deleteDbRows('invc.customer', pkeys=[victim])
        db.rollback()


def test_archive_db_rows(handlers, db, notes, an_invoice):  # noqa: F811
    """B15, B16, B18, B19: the deletion field takes midnight of the date."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        assert handler.archiveDbRows(NOTE_TABLE, pkeys=[pkey],
                                     archiveDate=datetime.date(2026, 1, 2)) is None
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['__del_ts'] == datetime.datetime(2026, 1, 2)


def test_archive_db_rows_without_a_date_unarchives(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """B16: no archiveDate writes None, which brings the rows back."""
    pkeys = twin_notes(db, notes, an_invoice,
                       __del_ts=datetime.datetime(2026, 1, 2))
    for handler, pkey in zip(handlers, pkeys):
        handler.archiveDbRows(NOTE_TABLE, pkeys=[pkey])
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['__del_ts'] is None


def test_archive_db_rows_leaves_the_protected_alone(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """B17: protectPkeys means "do not touch", the opposite of deleteDbRows."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        handler.archiveDbRows(NOTE_TABLE, pkeys=[pkey], protectPkeys=[pkey],
                              archiveDate=datetime.date(2026, 1, 2))
    assert_twins_agree(db, pkeys)
    assert note_row(db, pkeys[0])['__del_ts'] is None


def test_archive_db_rows_has_no_permission_check(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """B14: a table closed to deletion is archived all the same."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        handler.page.permission_calls.clear()
        handler.page.forbidden_permissions = {'del'}
        handler.archiveDbRows(NOTE_TABLE, pkeys=[pkey],
                              archiveDate=datetime.date(2026, 1, 2))
        handler.page.forbidden_permissions = set()
        assert handler.page.permission_calls == []
    assert_twins_agree(db, pkeys)


def test_duplicate_db_rows(handlers, db, notes, an_invoice):  # noqa: F811
    """B22, B24-B26: the copies hold the same content and their pkeys come back."""
    pkeys = twin_notes(db, notes, an_invoice, note_text='to duplicate')
    copies = []
    for handler, pkey in zip(handlers, pkeys):
        result = handler.duplicateDbRows(NOTE_TABLE, pkeys=[pkey])
        assert len(result) == 1
        copies.append(note_row(db, result[0]))
    assert copies[0] == copies[1]
    assert copies[0]['note_text'] == 'to duplicate'


def test_duplicate_db_rows_ignores_commit(handlers, db, notes, an_invoice):  # noqa: F811
    """B25: commit=False still commits, in both handlers."""
    pkeys = twin_notes(db, notes, an_invoice)
    for handler, pkey in zip(handlers, pkeys):
        newpkey = handler.duplicateDbRows(NOTE_TABLE, pkeys=[pkey], commit=False)[0]
        db.rollback()
        assert note_row(db, newpkey) is not None


def test_touch_grid_selected_rows(handlers, db, notes, an_invoice):  # noqa: F811
    """B31-B32: the rows go through the update triggers and stay as they were.

    ``touchRecords`` marks the row ``_notUserChange``, so ``__mod_ts`` does not
    move: what the touch does is run the triggers again, and on a table with
    none — which is the case here — nothing changes at all.  The case is the
    proof that the call reaches the table and leaves the row alone, in both
    handlers.
    """
    pkeys = twin_notes(db, notes, an_invoice)
    before = [db.table(NOTE_TABLE).record(pkey).output('dict')['__mod_ts']
              for pkey in pkeys]
    for handler, pkey in zip(handlers, pkeys):
        assert handler.touchGridSelectedRows(table=NOTE_TABLE,
                                             pkeys=[pkey]) is None
    after = [db.table(NOTE_TABLE).record(pkey).output('dict')['__mod_ts']
             for pkey in pkeys]
    assert after == before
    assert_twins_agree(db, pkeys)


def test_delete_file_rows(storage_handlers):
    """B28-B29: a comma separated string and a list both delete the files."""
    legacy, nxt, root = storage_handlers
    for i, handler in enumerate((legacy, nxt)):
        one = root / ('one_%i.txt' % i)
        two = root / ('two_%i.txt' % i)
        one.write_text('a')
        two.write_text('b')
        files = '%s,%s' % (one.name, two.name) if i == 0 else [one.name, two.name]
        handler.deleteFileRows(files=files)
        assert not one.exists()
        assert not two.exists()


def test_update_checkbox_pkeys(handlers, db, customers):  # noqa: F811
    """B36-B37: the value the caller sent lands in the column."""
    tblobj = db.table('invc.customer')
    for handler in handlers:
        pkey = customers.take(1)[0]
        handler.updateCheckboxPkeys(table='invc.customer', field='__is_draft',
                                    changesDict={pkey: False})
        row = tblobj.query(columns='$__is_draft', where='$id=:p', p=pkey,
                           excludeDraft=False).fetch()[0]
        assert row['__is_draft'] in (False, 0)


def test_update_checkbox_pkeys_is_a_radio_group(handlers, db, customers):  # noqa: F811
    """B34-B35: _fields is popped, and every other field is set to False."""
    tblobj = db.table('invc.customer')
    written = []
    for handler in handlers:
        pkey = customers.take(1)[0]
        with tblobj.recordToUpdate(pkey) as record:
            record['notes'] = 'something'
        db.commit()
        changes = {pkey: True, '_fields': ['__is_draft', 'notes']}
        handler.updateCheckboxPkeys(table='invc.customer', field='__is_draft',
                                    changesDict=changes)
        assert changes == {pkey: True}, '_fields must be popped out'
        row = tblobj.query(columns='$__is_draft,$notes', where='$id=:p', p=pkey,
                           excludeDraft=False).fetch()[0]
        written.append((row['__is_draft'], row['notes']))
    assert written[0] == written[1]
    assert written[0][1] in (False, 0, '0', 'false')


def test_update_checkbox_pkeys_without_changes(handlers):
    """B33: an empty changesDict returns without touching the database."""
    for handler in handlers:
        assert handler.updateCheckboxPkeys(table='invc.customer',
                                           field='__is_draft',
                                           changesDict=None) is None


# ---------------------------------------------------------------------------
#  Flow C — frozen selections
# ---------------------------------------------------------------------------

def freeze_on_both(handlers, db, name, table=NOTE_TABLE, **querypars):
    """Freeze the same selection under *name* on both stand-in pages.

    The two handlers have their own connection folder, so each one gets its own
    pickle of an identically built selection.

    Returns:
        The selection the last handler froze, for the assertions that need its
        rows.
    """
    selection = None
    for handler in handlers:
        selection = db.table(table).query(**querypars).selection()
        handler.page.freezeSelection(selection, name)
    return selection


def test_freezed_selection_pkeys(handlers, db):  # noqa: F811
    """C1-C3: the pkeys of the frozen selection, in its order."""
    selection = freeze_on_both(handlers, db, 'fs_plain',
                               columns='$note_text', limit=5, order_by='$id')
    expected = [r['pkey'] for r in selection.output('dictlist')]
    for handler in handlers:
        assert handler.freezedSelectionPkeys(table=NOTE_TABLE,
                                             selectionName='fs_plain') == expected


def test_freezed_selection_pkeys_caption_diverges(handlers, db):  # noqa: F811
    """C4, defect D9: the frozen handler reads the literal key 'caption_field'.

    The parameter names the column the caption comes from; the frozen handler
    uses it as a truthiness switch only and then looks up a column literally
    called ``caption_field``, which no table has.
    """
    legacy, nxt = handlers
    selection = freeze_on_both(handlers, db, 'fs_caption',
                               columns='$note_text', limit=3, order_by='$id')
    with pytest.raises(KeyError) as error:
        legacy.freezedSelectionPkeys(table=NOTE_TABLE, selectionName='fs_caption',
                                     caption_field='note_text')
    assert error.value.args[0] == 'caption_field'
    result = nxt.freezedSelectionPkeys(table=NOTE_TABLE,
                                       selectionName='fs_caption',
                                       caption_field='note_text')
    expected = [dict(pkey=r['pkey'], caption=r['note_text'])
                for r in selection.output('dictlist')]
    assert result == expected


def test_sum_on_freezed_selection(handlers, db):  # noqa: F811
    """C7: the sum comes back as a list, one item per column."""
    selection = freeze_on_both(handlers, db, 'fs_sum', columns='$priority',
                               limit=10, order_by='$id')
    expected = selection.sum('priority')
    assert isinstance(expected, list)
    for handler in handlers:
        assert handler.sumOnFreezedSelection(table=NOTE_TABLE,
                                             selectionName='fs_sum',
                                             sum_column='priority') == expected


def test_sum_on_freezed_selection_missing(handlers):
    """C6: a selection that was never frozen sums to the integer zero."""
    for handler in handlers:
        assert handler.sumOnFreezedSelection(table=NOTE_TABLE,
                                             selectionName='no_such_selection',
                                             sum_column='priority') == 0


def test_check_freezed_selection_missing(handlers):
    """C10: a selection that was never frozen never asks for a refresh."""
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='D', pkey='x')],
            selectionName='no_such_selection', table=NOTE_TABLE) is False


def test_check_freezed_selection_deleted(handlers, db):  # noqa: F811
    """C12: a deleted pkey inside the selection asks for a refresh."""
    selection = freeze_on_both(handlers, db, 'fs_del', columns='$note_text',
                               limit=4, order_by='$id')
    inside = selection.output('dictlist')[0]['pkey']
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='D', pkey=inside)],
            selectionName='fs_del', table=NOTE_TABLE) is True
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='D', pkey='outside')],
            selectionName='fs_del', table=NOTE_TABLE) is False


def test_check_freezed_selection_updated(handlers, db):  # noqa: F811
    """C13: an updated pkey inside the selection asks for a refresh."""
    selection = freeze_on_both(handlers, db, 'fs_upd', columns='$note_text',
                               limit=4, order_by='$id')
    inside = selection.output('dictlist')[0]['pkey']
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='U', pkey=inside)],
            selectionName='fs_upd', table=NOTE_TABLE) is True


def test_check_freezed_selection_probes_the_inserted(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """C15, C19-C20: a new row is a refresh only when it matches the filter."""
    freeze_on_both(handlers, db, 'fs_ins', columns='$note_text',
                   where="$note_type=:t", t='PROBE', order_by='$id')
    matching = twin_notes(db, notes, an_invoice, note_type='PROBE')[0]
    outsider = notes.take(1)[0]
    with db.table(NOTE_TABLE).recordToUpdate(outsider) as record:
        record['note_type'] = 'OTHER'
    db.commit()
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=matching)],
            selectionName='fs_ins', table=NOTE_TABLE,
            where="$note_type='PROBE'") is True
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=outsider)],
            selectionName='fs_ins', table=NOTE_TABLE,
            where="$note_type='PROBE'") is False


def test_check_freezed_selection_where_bag(handlers, db, notes, an_invoice):  # noqa: F811
    """C16: a Bag where goes through the where bag decoder of the core class."""
    freeze_on_both(handlers, db, 'fs_bag', columns='$note_text',
                   where="$note_type=:t", t='BAGPROBE', order_by='$id')
    matching = twin_notes(db, notes, an_invoice, note_type='BAGPROBE')[0]
    where = Bag()
    where.setItem('c_0', 'BAGPROBE', column='note_type', op='equal')
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=matching)],
            selectionName='fs_bag', table=NOTE_TABLE, where=where) is True


def test_check_freezed_selection_condition(handlers, db, notes, an_invoice):  # noqa: F811
    """C17: the caller's condition is AND-ed into the probe."""
    freeze_on_both(handlers, db, 'fs_cond', columns='$note_text',
                   limit=2, order_by='$id')
    matching = twin_notes(db, notes, an_invoice, note_type='CONDPROBE')[0]
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=matching)],
            selectionName='fs_cond', table=NOTE_TABLE,
            condition="$note_type='CONDPROBE'") is True
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=matching)],
            selectionName='fs_cond', table=NOTE_TABLE,
            condition="$note_type='SOMETHING ELSE'") is False


def test_check_freezed_selection_drops_where_attr_and_columns(handlers, db, notes, an_invoice):  # noqa: F811,E501
    """C14, C18: where_attr and columns are dropped before the probe runs."""
    freeze_on_both(handlers, db, 'fs_drop', columns='$note_text',
                   limit=2, order_by='$id')
    matching = twin_notes(db, notes, an_invoice, note_type='DROPPROBE')[0]
    for handler in handlers:
        assert handler.checkFreezedSelection(
            changelist=[dict(dbevent='I', pkey=matching)],
            selectionName='fs_drop', table=NOTE_TABLE,
            where_attr=Bag(), columns='$not_a_column',
            condition="$note_type='DROPPROBE'") is True


# ---------------------------------------------------------------------------
#  Flow D — grid rendering
# ---------------------------------------------------------------------------

def grid_selection(db, **querypars):
    """A small invoice selection for the grid rendering cases."""
    querypars.setdefault('columns', '$inv_number,$total,$date')
    querypars.setdefault('limit', 4)
    querypars.setdefault('order_by', '$inv_number')
    return db.table('invc.invoice').query(**querypars).selection()


def grid_shape(data):
    """The comparable shape of a grid data Bag."""
    return [(node.label, node.getStaticValue(), dict(node.attr)) for node in data]


def test_grid_selection_data(handlers, db):  # noqa: F811
    """D1-D3, D6-D7, D9-D10: the same rows, keys and attributes."""
    shapes = []
    for handler in handlers:
        selection = grid_selection(db)
        data = handler.gridSelectionData(
            selection, selection.output(mode='generator'), recordResolver=False,
            numberedRows=False, logicalDeletionField='__del_ts')
        shapes.append(grid_shape(data))
    assert shapes[0] == shapes[1]
    assert len(shapes[0]) == 4
    assert all('_pkey' in attr for _, _, attr in shapes[0])
    assert all('pkey' not in attr for _, _, attr in shapes[0]), (
        'the pkey is popped out of the row and only travels as _pkey')
    assert all('inv_number' in attr for _, _, attr in shapes[0])


def test_grid_selection_data_numbered_rows(handlers, db):  # noqa: F811
    """D6: with numberedRows the label is the position, not the pkey."""
    for handler in handlers:
        selection = grid_selection(db)
        data = handler.gridSelectionData(
            selection, selection.output(mode='generator'), recordResolver=False,
            numberedRows=True, logicalDeletionField=None)
        assert [node.label for node in data] == ['r_0', 'r_1', 'r_2', 'r_3']
        assert all(node.attr['_pkey'] != node.label for node in data)


def test_grid_selection_data_record_resolver(handlers, db):  # noqa: F811
    """D8: the resolver attributes name the table and the literal resolver."""
    for handler in handlers:
        selection = grid_selection(db)
        node = list(handler.gridSelectionData(
            selection, selection.output(mode='generator'), recordResolver=True,
            numberedRows=False, logicalDeletionField=None))[0]
        assert node.attr['_target_fld'] == 'invc.invoice.id'
        assert node.attr['_resolver_name'] == 'relOneResolver'
        assert node.attr['_relation_value'] == node.attr['_pkey']


def test_grid_selection_data_logically_deleted_row(handlers, db):  # noqa: F811
    """D4: the class comes from the row's _isdeleted, not from the parameter."""
    rows = [dict(pkey='a', _isdeleted=True, inv_number='X'),
            dict(pkey='b', _isdeleted=None, inv_number='Y')]
    classes = []
    for handler in handlers:
        selection = grid_selection(db)
        data = handler.gridSelectionData(selection, list(rows),
                                         recordResolver=False,
                                         numberedRows=False,
                                         logicalDeletionField=None)
        classes.append([node.attr['_customClasses'] for node in data])
    assert classes[0] == classes[1]
    assert classes[0] == [' logicalDeleted', ''], (
        'the empty class list of the row leaves a leading space, in both')


def test_grid_selection_data_add_classes(handlers, db):  # noqa: F811
    """D5: the three shapes of an _addClassesDict entry."""
    rows = [dict(pkey='a', state='ok', flag='on', plain='p', empty=''),
            dict(pkey='b', state='ko', flag=None, plain='p', empty='')]
    addClasses = dict(state=dict(ok='green', ko='red'), flag=True,
                      plain='constant', empty=True)
    classes = []
    for handler in handlers:
        selection = grid_selection(db)
        data = handler.gridSelectionData(selection, list(rows),
                                         recordResolver=False,
                                         numberedRows=False,
                                         logicalDeletionField=None,
                                         _addClassesDict=addClasses)
        classes.append([node.attr['_customClasses'] for node in data])
    assert classes[0] == classes[1]
    assert classes[0] == [' green on constant', ' red constant']


def test_grid_selection_struct(handlers, db):  # noqa: F811
    """D12-D18: the same cells, with the same widths."""
    structs = []
    for handler in handlers:
        structs.append(handler.gridSelectionStruct(grid_selection(db)))
    assert structs[0].toXml() == structs[1].toXml()
    cells = structs[0]['view_0.row_0']
    assert [node.label for node in cells] == ['inv_number', 'total', 'date']
    assert cells.getAttr('date', 'format_date') == 'short'
    assert cells.getAttr('inv_number', 'name') == '!!Invoice number'
    assert 'label' not in cells.getNode('inv_number').attr


class _SizedSelection:
    """A selection whose only job is to declare one column per size.

    ``gridSelectionStruct`` reads two things off a selection, ``columns`` and
    ``colAttrs``; this stand-in declares exactly those, so both handlers run
    their real width block over every size the branch can see.
    """

    def __init__(self, sizes):
        self.columns = ['c_%s' % i for i, _ in enumerate(sizes)]
        self.colAttrs = dict([(name, dict(label=name, dataType='T', size=size))
                              for name, size in zip(self.columns, sizes)])


def test_grid_selection_struct_narrow_columns_agree(handlers):  # noqa: F811
    """D17: the missing elif of the frozen handler changes no width.

    For a size below three the frozen handler computes ``size * 1.1`` and then
    overwrites it with ``size``; the ``int()`` of the next line erases the
    difference, so the two readings give the same ``em`` for every size the
    branch can see.  Both structures come out of the real
    ``gridSelectionStruct`` of each handler.
    """
    sizes = list(range(0, 40)) + ['3:12', None]
    structs = [handler.gridSelectionStruct(_SizedSelection(sizes))
               for handler in handlers]
    assert structs[0].toXml() == structs[1].toXml()
    cells = structs[0]['view_0.row_0']
    assert cells.getAttr('c_0', 'width') is None
    assert cells.getAttr('c_1', 'width') == '%iem' % (1 + int(int(1) * .7))
    assert cells.getAttr('c_40', 'width') == cells.getAttr('c_12', 'width')
    assert cells.getAttr('c_41', 'width') is None


def test_get_fieldcell_pars(handlers, db):  # noqa: F811
    """D20-D22: the same cell parameters, with the field the caller asked for."""
    results = []
    for handler in handlers:
        results.append(handler.getFieldcellPars(field='customer_id',
                                                table='invc.invoice'))
    assert results[0].asDict(ascii=True) == results[1].asDict(ascii=True)
    assert results[0]['field'] == 'customer_id'
    assert results[0]['related_table'] == 'invc.customer'


# ---------------------------------------------------------------------------
#  Flow E — file system and relation captions
# ---------------------------------------------------------------------------

def write_documents(root):
    """Two XML documents, one text file and an empty folder under *root*."""
    folder = root / 'docs'
    folder.mkdir()
    (folder / 'sub').mkdir()
    Bag(dict(name='One', description='first')).toXml(str(folder / 'a.xml'))
    Bag(dict(name='Two', description='second')).toXml(str(folder / 'b.xml'))
    (folder / 'plain.txt').write_text('hello')
    return folder


def file_shape(data):
    """The comparable shape of a file selection, without the volatile values."""
    volatile = ('mtime', 'created_ts', 'changed_ts', 'size')
    return [(node.label, {k: v for k, v in node.attr.items() if k not in volatile})
            for node in data]


def test_get_file_system_selection_flat(storage_handlers):
    """E2-E5, E7, E9: the same rows, with the pkey and the XML columns."""
    legacy, nxt, root = storage_handlers
    write_documents(root)
    shapes = []
    for handler in (legacy, nxt):
        result, attributes = handler.getFileSystemSelection(
            folders='docs', columns='name,description')
        assert attributes == {}
        shapes.append(file_shape(result))
    assert shapes[0] == shapes[1]
    labels = [label for label, _ in shapes[0]]
    assert len(labels) == 3, 'the folder and the subfolder are not rows'
    first = dict(shapes[0])[labels[0]]
    assert first['_pkey'] == first['abs_path']
    assert first['name'] == 'One'
    assert first['description'] == 'first'


def test_get_file_system_selection_timestamps_both_come_from_mtime(storage_handlers):
    """E2: the storage resolver publishes no creation time, so the two agree."""
    legacy, nxt, root = storage_handlers
    write_documents(root)
    for handler in (legacy, nxt):
        result, _ = handler.getFileSystemSelection(folders='docs')
        for node in result:
            assert node.attr['created_ts'] == node.attr['changed_ts']
            assert node.attr['created_ts'] == datetime.datetime.fromtimestamp(
                node.attr['mtime'])


def test_get_file_system_selection_hierarchical(storage_handlers):
    """E6: the hierarchical branch returns the tree Bag bare, folders included."""
    legacy, nxt, root = storage_handlers
    write_documents(root)
    trees = []
    for handler in (legacy, nxt):
        tree = handler.getFileSystemSelection(folders='docs', hierarchical=True)
        assert isinstance(tree, Bag)
        trees.append([(node.label, node.attr.get('file_ext'))
                      for node in tree['docs']])
    assert trees[0] == trees[1]
    assert ('sub', 'directory') in trees[0]


def test_get_file_system_selection_applymethod(storage_handlers):
    """E8: the applymethod receives the rows and its result becomes attributes."""
    legacy, nxt, root = storage_handlers
    write_documents(root)
    seen = []
    for handler in (legacy, nxt):
        def applymethod(rows, **kwargs):
            seen.append((len(rows), kwargs))
            return dict(filecount=len(rows))

        handler.page.rpc_methods['countfiles'] = applymethod
        result, attributes = handler.getFileSystemSelection(
            folders='docs', applymethod='countfiles', apply_greeting='hello')
        assert attributes == dict(filecount=len(result))
    assert seen[0] == seen[1]
    assert seen[0][1] == dict(greeting='hello')


def test_get_file_system_selection_ext_loses_the_attributes(storage_handlers):
    """E10: with ext the XML rows lose their pkey, in both handlers.

    The guard is ``if not node.value``, meant as "a file, not a folder".  With
    ``ext='xml'`` the resolver installs an ``XmlStorageResolver`` as the value
    of every XML node, the guard turns false and those rows reach the client
    without ``_pkey``, without the timestamps and without the columns — while
    the ``txt`` row next to them keeps all three.  Reproduced, not fixed: see
    ``bugs_misc.md``.
    """
    legacy, nxt, root = storage_handlers
    write_documents(root)
    shapes = []
    for handler in (legacy, nxt):
        result, _ = handler.getFileSystemSelection(folders='docs', ext='xml',
                                                   columns='name,description')
        shapes.append([(node.attr['file_ext'], '_pkey' in node.attr,
                        'name' in node.attr) for node in result])
    assert shapes[0] == shapes[1]
    assert ('xml', False, False) in shapes[0]
    assert ('txt', True, False) in shapes[0]


def test_rel_path_to_caption(handlers):
    """E11-E13: the same caption, and the empty path short circuits."""
    captions = [handler._relPathToCaption('invc.invoice_row',
                                          '@invoice_id.@customer_id.account_name')
                for handler in handlers]
    assert captions[0] == captions[1]
    assert ':' in captions[0]
    assert all(handler._relPathToCaption('invc.invoice_row', '') == ''
               for handler in handlers)
