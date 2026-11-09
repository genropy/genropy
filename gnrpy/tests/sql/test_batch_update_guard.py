"""Tests for the row-selection guard of batchUpdate and touchRecords.

Covers issue #1021: a call carrying no row selection at all (no ``where``,
no ``pkey``, no ``_pkeys``) used to return ``None`` without touching a
single row, without logging and without raising, while a caller passing an
explicitly empty selection (``_pkeys=[]`` / ``None``) legitimately expects
a no-op. The two cases are now told apart by a sentinel default.

Both mixins are covered because the guard lives in a single helper shared
by ``CrudMixin.batchUpdate`` and ``TriggersMixin.touchRecords``.

Runs against the SQLite and the PostgreSQL instances of the test_invoice
project.
"""

import datetime
import uuid

import pytest

from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException
from gnr.sql.gnrsqltable.helpers import prepare_batch_selection

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(params=['db_sqlite', 'db_pg'])
def db(request):
    """Run every test on both implementations."""
    return request.getfixturevalue(request.param)


def _tag():
    """Return a marker unique to a single assertion."""
    return 'issue1021-%s' % uuid.uuid4().hex[:12]


def _logically_delete(tbl, pkey):
    """Logically delete a record by setting its logical deletion field."""
    row = tbl.query(where='$%s=:pk' % tbl.pkey, pk=pkey,
                    for_update=True).fetch()[0]
    old_record = dict(row)
    old_record.pop('pkey', None)
    record = dict(old_record)
    record[tbl.logicalDeletionField] = datetime.datetime.now()
    tbl.update(record, old_record=old_record)
    tbl.db.commit()


def _hard_delete(tbl, pkeys):
    """Physically remove the scratch records, drafts and archived included."""
    rows = tbl.query(where='$%s IN :pk' % tbl.pkey, pk=list(pkeys),
                     excludeDraft=False, excludeLogicalDeleted=False,
                     for_update=True).fetch()
    for row in rows:
        tbl.delete(dict(row))
    tbl.db.commit()


def _notes(tbl, pkeys):
    """Return ``{pkey: notes}`` for the given records, whatever their state."""
    rows = tbl.query(where='$%s IN :pk' % tbl.pkey, pk=list(pkeys),
                     columns='$%s,$notes' % tbl.pkey,
                     excludeDraft=False, excludeLogicalDeleted=False).fetch()
    return {row[tbl.pkey]: row['notes'] for row in rows}


def _tagged(tbl, tag):
    """Return the pkeys carrying *tag*, drafts and archived included."""
    rows = tbl.query(where='$notes=:t', t=tag, columns='$%s' % tbl.pkey,
                     excludeDraft=False, excludeLogicalDeleted=False).fetch()
    return {row[tbl.pkey] for row in rows}


def _visible(tbl):
    """Return the pkeys the ``where`` flow acts on (no draft, no archived)."""
    rows = tbl.query(where='$%s IS NOT NULL' % tbl.pkey,
                     columns='$%s' % tbl.pkey).fetch()
    return {row[tbl.pkey] for row in rows}


@pytest.fixture
def rows(db):
    """Three plain records, one draft and one logically deleted one."""
    tbl = db.table('invc.customer')
    marker = 'ISSUE1021 %s' % uuid.uuid4().hex[:8]
    plain = [tbl.insert(dict(account_name='%s p%i' % (marker, i)))[tbl.pkey]
             for i in range(3)]
    draft = tbl.insert(dict(account_name='%s draft' % marker,
                            **{tbl.draftField: True}))[tbl.pkey]
    deleted = tbl.insert(dict(account_name='%s deleted' % marker))[tbl.pkey]
    db.commit()
    _logically_delete(tbl, deleted)
    created = dict(plain=plain, draft=draft, deleted=deleted,
                   all=plain + [draft, deleted])
    yield created
    _hard_delete(tbl, created['all'])


class TestBatchUpdateSelection:

    def test_explicit_where_updates_every_visible_row(self, db, rows):
        """The positive control: the explicit where flow still writes."""
        tbl = db.table('invc.customer')
        tag = _tag()
        visible = _visible(tbl)
        assert set(rows['plain']) <= visible
        updated = tbl.batchUpdate(dict(notes=tag),
                                  where='$%s IS NOT NULL' % tbl.pkey)
        db.commit()
        assert set(updated) == visible
        assert _tagged(tbl, tag) == visible
        # the where flow keeps the standard draft / logical deletion
        # filters, so it is not a synonym of "every row of the table"
        assert rows['draft'] not in visible
        assert rows['deleted'] not in visible

    def test_no_selection_raises_without_touching_any_row(self, db, rows):
        tbl = db.table('invc.customer')
        tag = _tag()
        before = _notes(tbl, rows['all'])
        with pytest.raises(GnrSqlBusinessLogicException):
            tbl.batchUpdate(dict(notes=tag))
        db.commit()
        assert _tagged(tbl, tag) == set()
        assert _notes(tbl, rows['all']) == before

    @pytest.mark.parametrize('selection', [
        dict(_pkeys=[]),
        dict(_pkeys=None),
        dict(pkey=None),
    ], ids=['empty_pkeys', 'none_pkeys', 'none_pkey'])
    def test_explicitly_empty_selection_is_a_silent_noop(self, db, rows,
                                                         selection):
        """The contract of btcbase.batchUpdate and of updateParentFullTs."""
        tbl = db.table('invc.customer')
        tag = _tag()
        before = _notes(tbl, rows['all'])
        assert tbl.batchUpdate(dict(notes=tag), **selection) is None
        db.commit()
        assert _tagged(tbl, tag) == set()
        assert _notes(tbl, rows['all']) == before

    def test_single_pkey_updates_exactly_one_row(self, db, rows):
        tbl = db.table('invc.customer')
        tag = _tag()
        target = rows['plain'][0]
        tbl.batchUpdate(dict(notes=tag), pkey=target)
        db.commit()
        assert _tagged(tbl, tag) == {target}

    def test_pkeys_string_updates_exactly_its_rows(self, db, rows):
        tbl = db.table('invc.customer')
        tag = _tag()
        tbl.batchUpdate(dict(notes=tag), _pkeys=','.join(rows['plain']))
        db.commit()
        assert _tagged(tbl, tag) == set(rows['plain'])

    def test_pkeys_string_ignores_the_spaces_after_the_commas(self, db,
                                                             rows):
        """A ', '.join() selection updates every key, not just the first."""
        tbl = db.table('invc.customer')
        tag = _tag()
        tbl.batchUpdate(dict(notes=tag), _pkeys=', '.join(rows['plain']))
        db.commit()
        assert _tagged(tbl, tag) == set(rows['plain'])

    @pytest.mark.parametrize('_pkeys', [',', ' , ', ''],
                             ids=['comma', 'spaced_comma', 'empty'])
    def test_pkeys_string_of_separators_only_is_a_noop(self, db, rows,
                                                       _pkeys):
        tbl = db.table('invc.customer')
        tag = _tag()
        before = _notes(tbl, rows['all'])
        assert tbl.batchUpdate(dict(notes=tag), _pkeys=_pkeys) is None
        db.commit()
        assert _tagged(tbl, tag) == set()
        assert _notes(tbl, rows['all']) == before

    def test_falsy_pkey_is_a_selection_not_a_silent_skip(self, db, rows):
        """Only None is the deliberate no-op: '' names a row that is absent.

        The empty list tells the query flow apart from the guard's early
        return, which yields None.
        """
        tbl = db.table('invc.customer')
        tag = _tag()
        assert tbl.batchUpdate(dict(notes=tag), pkey='') == []
        db.commit()
        assert _tagged(tbl, tag) == set()

    def test_explicit_where_none_stays_a_full_table_update(self, db, rows):
        """Pins the asymmetry the guard is built on.

        The branch is chosen on key presence, not on truth: ``where=None``
        passed explicitly falls through to the query and updates the whole
        visible table, while passing nothing at all now raises.
        """
        tbl = db.table('invc.customer')
        tag = _tag()
        visible = _visible(tbl)
        updated = tbl.batchUpdate(dict(notes=tag), where=None)
        db.commit()
        assert set(updated) == visible
        assert set(rows['plain']) <= _tagged(tbl, tag)
        assert rows['draft'] not in visible
        assert rows['deleted'] not in visible


class TestTouchRecordsSelection:
    """The same five shapes on the sibling that shares the guard."""

    def test_explicit_where_touches_every_visible_row(self, db, rows):
        tbl = db.table('invc.customer')
        visible = _visible(tbl)
        sel = tbl.touchRecords(where='$%s IS NOT NULL' % tbl.pkey)
        db.commit()
        assert {row[tbl.pkey] for row in sel} == visible

    def test_no_selection_raises(self, db, rows):
        tbl = db.table('invc.customer')
        before = _notes(tbl, rows['all'])
        with pytest.raises(GnrSqlBusinessLogicException):
            tbl.touchRecords()
        db.commit()
        assert _notes(tbl, rows['all']) == before

    @pytest.mark.parametrize('selection', [
        dict(_pkeys=[]),
        dict(_pkeys=None),
        dict(pkey=None),
    ], ids=['empty_pkeys', 'none_pkeys', 'none_pkey'])
    def test_explicitly_empty_selection_is_a_silent_noop(self, db, rows,
                                                         selection):
        tbl = db.table('invc.customer')
        assert tbl.touchRecords(**selection) is None

    def test_single_pkey_touches_exactly_one_row(self, db, rows):
        tbl = db.table('invc.customer')
        target = rows['plain'][0]
        sel = tbl.touchRecords(pkey=target)
        db.commit()
        assert [row[tbl.pkey] for row in sel] == [target]

    def test_pkeys_string_touches_exactly_its_rows(self, db, rows):
        tbl = db.table('invc.customer')
        sel = tbl.touchRecords(_pkeys=','.join(rows['plain']))
        db.commit()
        assert {row[tbl.pkey] for row in sel} == set(rows['plain'])

    def test_pkeys_string_ignores_the_spaces_after_the_commas(self, db,
                                                             rows):
        tbl = db.table('invc.customer')
        sel = tbl.touchRecords(_pkeys=', '.join(rows['plain']))
        db.commit()
        assert {row[tbl.pkey] for row in sel} == set(rows['plain'])

    @pytest.mark.parametrize('_pkeys', [',', ' , ', ''],
                             ids=['comma', 'spaced_comma', 'empty'])
    def test_pkeys_string_of_separators_only_is_a_noop(self, db, rows,
                                                       _pkeys):
        tbl = db.table('invc.customer')
        assert tbl.touchRecords(_pkeys=_pkeys) is None

    def test_falsy_pkey_is_a_selection_not_a_silent_skip(self, db, rows):
        tbl = db.table('invc.customer')
        assert tbl.touchRecords(pkey='') == []

    def test_explicit_where_none_stays_a_full_table_touch(self, db, rows):
        tbl = db.table('invc.customer')
        visible = _visible(tbl)
        sel = tbl.touchRecords(where=None)
        db.commit()
        assert {row[tbl.pkey] for row in sel} == visible


class TestSelectionNormalization:
    """The helper itself, on the shapes the DB flow cannot express.

    ``invc.customer`` has a text pkey, so a numeric key can only be pinned
    on the normalization step, without reaching the query.
    """

    def test_zero_pkey_names_a_row(self, db):
        tbl = db.table('invc.customer')
        kwargs = {}
        assert prepare_batch_selection(tbl, kwargs, pkey=0) is False
        assert kwargs['_pkeys'] == [0]

    def test_none_pkey_is_the_only_empty_selection(self, db):
        tbl = db.table('invc.customer')
        kwargs = {}
        assert prepare_batch_selection(tbl, kwargs, pkey=None) is True
        assert kwargs == {}
