#!/usr/bin/env python3
# encoding: utf-8
"""Tests for HierarchicalHandler (issues #987, #1523, #1524, #1527).

When a hierarchical table has a counter, ``_row_count`` is auto-assigned on
insert if the caller does not supply one. That assignment must happen *before*
the ``hierarchical_<field>`` paths are built, because ``_row_count`` can itself
be declared as one of the hierarchical fields: otherwise a literal Python
``None`` is interpolated into the path (``NULL`` for roots, ``'None/None'`` for
children), and it silently self-heals only on the next update of the record.

Two tables of the test_invoice project are exercised:

* ``invc.product_type`` — ``hierarchical='description', counter=True``:
  ``_row_count`` is not a hierarchical field, so nothing may change there.
* ``invc.product_group`` — ``hierarchical='code,_row_count', counter=True``:
  the case reported in the issue.

Both use the module-scoped ``db_sqlite`` fixture from this directory's conftest,
so they run on a real database without needing PostgreSQL.
"""

import datetime

import pytest

from gnr.core.gnrstring import encode36
from gnr.sql.gnrsqltable import GnrSqlBusinessLogicException, GnrSqlStandardException

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _fetch_one(tbl, where, **kwargs):
    rows = tbl.query(where=where, subtable='*', addPkeyColumn=False,
                     excludeLogicalDeleted=False, **kwargs).fetch()
    assert len(rows) == 1, 'expected exactly one row, got %i' % len(rows)
    return rows[0]


def _fetch_children(tbl, parent_id):
    return tbl.query(where='$parent_id=:p_id', p_id=parent_id, subtable='*',
                     addPkeyColumn=False, order_by='$_row_count').fetch()


def _last_root_counter(tbl):
    return tbl.readColumns(columns='$_row_count', where='$parent_id IS NULL',
                           subtable='*', order_by='$_row_count desc', limit=1) or 0


class TestHierarchicalCounterNotAHierarchicalField:
    """invc.product_type: hierarchical='description', counter=True.

    Non-regression: moving the counter assignment above the hierarchical loop
    must leave counters, ``_h_count`` chain and hierarchical paths untouched,
    and must not skip the loop for tables that reach the early return.
    """

    def test_root_and_children_counters(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        expected_root_counter = _last_root_counter(tbl) + 1

        tbl.insert(dict(description='hgroup root'))
        db.commit()
        root = _fetch_one(tbl, '$description=:d', d='hgroup root')
        assert root['_row_count'] == expected_root_counter
        assert root['_h_count'] == encode36(expected_root_counter, 2)
        assert root['_parent_h_count'] is None
        assert root['hierarchical_description'] == 'hgroup root'
        assert root['_parent_h_description'] is None
        assert root['hierarchical_pkey'] == root['id']

        for description in ('hgroup c1', 'hgroup c2', 'hgroup c3'):
            tbl.insert(dict(description=description, parent_id=root['id']))
        db.commit()

        children = _fetch_children(tbl, root['id'])
        assert [r['description'] for r in children] == ['hgroup c1', 'hgroup c2',
                                                        'hgroup c3']
        assert [r['_row_count'] for r in children] == [1, 2, 3]
        assert [r['_h_count'] for r in children] == [
            '%s%s' % (root['_h_count'], encode36(k, 2)) for k in (1, 2, 3)]
        assert [r['_parent_h_count'] for r in children] == [root['_h_count']] * 3
        assert [r['hierarchical_description'] for r in children] == [
            'hgroup root/hgroup c1', 'hgroup root/hgroup c2',
            'hgroup root/hgroup c3']
        assert [r['_parent_h_description'] for r in children] == ['hgroup root'] * 3
        assert [r['hierarchical_pkey'] for r in children] == [
            '%s/%s' % (root['id'], r['id']) for r in children]

    def test_copy_from_parent_still_runs_for_grandchildren(self, db_sqlite):
        """The early return sits after the loop: a third level still gets its
        paths built from the parent record."""
        db = db_sqlite
        tbl = db.table('invc.product_type')
        parent = _fetch_one(tbl, '$description=:d', d='hgroup c1')
        tbl.insert(dict(description='hgroup gc1', parent_id=parent['id']))
        db.commit()
        grandchild = _fetch_one(tbl, '$description=:d', d='hgroup gc1')
        assert grandchild['_row_count'] == 1
        assert grandchild['hierarchical_description'] == \
            'hgroup root/hgroup c1/hgroup gc1'
        assert grandchild['_h_count'] == '%s%s' % (parent['_h_count'],
                                                  encode36(1, 2))


class TestCounterUsedAsHierarchicalField:
    """invc.product_group: hierarchical='code,_row_count', counter=True.

    This is the issue #987 regression: before the fix the root stored NULL and
    the child the literal string 'None/None' in hierarchical__row_count.
    """

    def test_auto_assigned_counter_reaches_the_hierarchical_path(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_group')
        assert tbl.attributes['hierarchical'] == 'code,_row_count,pkey'

        tbl.insert(dict(code='A', description='group A'))
        db.commit()
        root = _fetch_one(tbl, '$code=:c', c='A')
        assert root['_row_count'] == 1
        assert root['_h_count'] == '01'
        # was None before the fix
        assert root['hierarchical__row_count'] == '1'
        assert root['hierarchical_code'] == 'A'

        tbl.insert(dict(code='B', description='group B', parent_id=root['id']))
        db.commit()
        child = _fetch_one(tbl, '$code=:c', c='B')
        assert child['_row_count'] == 1
        assert child['_h_count'] == '0101'
        assert child['_parent_h__row_count'] == '1'
        # was the literal 'None/None' before the fix
        assert child['hierarchical__row_count'] == '1/1'
        assert child['hierarchical_code'] == 'A/B'

    def test_siblings_get_distinct_paths_and_no_none_segment(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_group')
        root_counter = _last_root_counter(tbl) + 1
        tbl.insert(dict(code='S', description='siblings root'))
        db.commit()
        root = _fetch_one(tbl, '$code=:c', c='S')
        assert root['_row_count'] == root_counter
        assert root['hierarchical__row_count'] == str(root_counter)

        for code in ('S1', 'S2', 'S3'):
            tbl.insert(dict(code=code, parent_id=root['id']))
        db.commit()

        children = _fetch_children(tbl, root['id'])
        assert [r['_row_count'] for r in children] == [1, 2, 3]
        assert [r['hierarchical__row_count'] for r in children] == [
            '%s/%i' % (root_counter, k) for k in (1, 2, 3)]

        # nothing in the whole table carries a literal 'None' segment
        allrows = tbl.query(columns='$hierarchical__row_count,$hierarchical_code',
                            subtable='*', addPkeyColumn=False).fetch()
        assert allrows
        for row in allrows:
            for fld in ('hierarchical__row_count', 'hierarchical_code'):
                assert 'None' not in (row[fld] or ''), \
                    'literal None in %s: %r' % (fld, row[fld])


def _insert_chain(db, tbl, *descriptions):
    """Insert a chain of nodes, each one child of the previous, and return them."""
    parent_id = None
    for description in descriptions:
        tbl.insert(dict(description=description, parent_id=parent_id))
        parent_id = _fetch_one(tbl, '$description=:d', d=description)['id']
    db.commit()
    return [_fetch_one(tbl, '$description=:d', d=d) for d in descriptions]


def _move(tbl, node_id, parent_id):
    """Move a node as ht_moveHierarchical does (resources/common/th/th_tree.py)."""
    tbl.batchUpdate(dict(parent_id=parent_id), where='$id=:pkey', pkey=node_id)


def _set_deleted(tbl, node_id, deleted):
    tbl.batchUpdate({'__del_ts': datetime.datetime.now() if deleted else None},
                    where='$id=:pkey', pkey=node_id, excludeLogicalDeleted=False)


class TestMoveUnderDescendant:
    """#1523: moving a node under itself or one of its descendants is refused."""

    @pytest.mark.parametrize('target', [0, 1, 2], ids=['self', 'child', 'grandchild'])
    def test_cycle_is_refused(self, db_sqlite, target):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        chain = _insert_chain(db, tbl, *('cyc%i %s' % (target, k) for k in 'abc'))
        with pytest.raises(GnrSqlBusinessLogicException):
            _move(tbl, chain[0]['id'], chain[target]['id'])
        db.rollback()
        for before in chain:
            after = _fetch_one(tbl, '$id=:pk', pk=before['id'])
            assert after['parent_id'] == before['parent_id']
            assert after['hierarchical_pkey'] == before['hierarchical_pkey']
            assert after['hierarchical_description'] == before['hierarchical_description']

    def test_legit_move_rewrites_the_subtree(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        a, b, c = _insert_chain(db, tbl, 'mv a', 'mv b', 'mv c')
        _move(tbl, b['id'], None)
        db.commit()
        b = _fetch_one(tbl, '$id=:pk', pk=b['id'])
        c = _fetch_one(tbl, '$id=:pk', pk=c['id'])
        assert b['hierarchical_pkey'] == b['id']
        assert b['hierarchical_description'] == 'mv b'
        assert c['hierarchical_pkey'] == '%s/%s' % (b['id'], c['id'])
        assert c['hierarchical_description'] == 'mv b/mv c'


class TestLogicallyDeletedNodes:
    """#1524: parent and children lookups ignore the logical-deletion filter."""

    def test_child_inserted_under_deleted_parent(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        (parent,) = _insert_chain(db, tbl, 'ldel p1')
        _set_deleted(tbl, parent['id'], True)
        db.commit()
        tbl.insert(dict(description='ldel c1', parent_id=parent['id']))
        db.commit()
        child = _fetch_one(tbl, '$description=:d', d='ldel c1')
        assert child['hierarchical_description'] == 'ldel p1/ldel c1'
        assert child['_parent_h_description'] == 'ldel p1'
        assert child['hierarchical_pkey'] == '%s/%s' % (parent['id'], child['id'])

    def test_restore_of_parent_keeps_children_paths(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        parent, child = _insert_chain(db, tbl, 'ldel p2', 'ldel c2')
        _set_deleted(tbl, parent['id'], True)
        db.commit()
        _set_deleted(tbl, parent['id'], False)
        db.commit()
        child = _fetch_one(tbl, '$id=:pk', pk=child['id'])
        assert child['__del_ts'] is None
        assert child['hierarchical_description'] == 'ldel p2/ldel c2'
        assert child['hierarchical_pkey'] == '%s/%s' % (parent['id'], child['id'])

    def test_rename_reaches_deleted_children(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        parent, child = _insert_chain(db, tbl, 'ldel p3', 'ldel c3')
        _set_deleted(tbl, child['id'], True)
        db.commit()
        tbl.batchUpdate(dict(description='ldel p3x'), where='$id=:pkey', pkey=parent['id'])
        db.commit()
        child = _fetch_one(tbl, '$id=:pk', pk=child['id'])
        assert child['hierarchical_description'] == 'ldel p3x/ldel c3'
        assert child['_parent_h_description'] == 'ldel p3x'


class TestHandlerMinorDefects:
    """#1527: explicit errors and wrong results of HierarchicalHandler helpers."""

    def test_update_without_old_record_is_an_explicit_error(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        (node,) = _insert_chain(db, tbl, 'noold')
        record = dict(node)
        record['description'] = 'noold x'
        with pytest.raises(GnrSqlStandardException):
            tbl.update(record)
        db.rollback()

    def test_fix_row_count_on_roots(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        roots = tbl.query(where='$parent_id IS NULL', subtable='*', addPkeyColumn=False,
                          for_update=True).fetch()
        for k, row in enumerate(roots):
            if row['_row_count'] is not None:
                old_row = dict(row)
                row['_row_count'] = row['_row_count'] + 1000 + k
                tbl.update(row, old_row)
        db.commit()
        tbl.hierarchicalHandler.fixRowCount()
        db.commit()
        counters = [r['_row_count'] for r in tbl.query(
            where='$parent_id IS NULL', subtable='*', addPkeyColumn=False,
            columns='$_row_count', order_by='$_row_count').fetch()]
        assert counters == list(range(1, len(counters) + 1))

    def test_path_from_pkey_with_condition(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        parent, child = _insert_chain(db, tbl, 'pfp p', 'pfp c')
        handler = tbl.hierarchicalHandler
        expected = '%s.%s' % (parent['id'], child['id'])
        assert handler.pathFromPkey(pkey=child['id']) == expected
        assert handler.pathFromPkey(pkey=child['id'], condition='$description=:d',
                                    condition_d='pfp c') == expected
        assert handler.pathFromPkey(pkey=child['id'], condition='$description=:d',
                                    condition_d='other') is None

    def test_paths_from_pkeys_skip_nodes_outside_parent(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        root, child, grandchild = _insert_chain(db, tbl, 'gpp r', 'gpp c', 'gpp g')
        (other,) = _insert_chain(db, tbl, 'gpp other')
        pkeys = ','.join([grandchild['id'], other['id']])
        result = tbl.hierarchicalHandler.getHierarchicalPathsFromPkeys(
            pkeys=pkeys, parent_id=root['id'])
        assert result == '%s.%s' % (child['id'], grandchild['id'])

    @pytest.mark.parametrize('variant', ['hlv', 'hdepth'])
    def test_variant_on_non_hierarchical_table(self, db_sqlite, variant):
        tbl = db_sqlite.table('invc.invoice')
        with pytest.raises(Exception, match='%s variant only for hierarchical table' % variant):
            getattr(tbl, 'variantColumn_%s' % variant)('inv_number')
