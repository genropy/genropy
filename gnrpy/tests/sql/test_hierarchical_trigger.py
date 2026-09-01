#!/usr/bin/env python3
# encoding: utf-8
"""Tests for HierarchicalHandler.trigger_before (issue #987).

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

from gnr.core.gnrstring import encode36

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _fetch_one(tbl, where, **kwargs):
    rows = tbl.query(where=where, subtable='*', addPkeyColumn=False, **kwargs).fetch()
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
