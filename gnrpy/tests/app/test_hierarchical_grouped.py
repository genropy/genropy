"""Tree data of a flat table grouped by some of its fields
(TableBase.getHierarchicalData with ``hierarchical``).

Uses the shared test_invoice fixture from this directory's conftest:
``invc.state.region_code`` points to the flat ``invc.region``, which has
no caption_field, so its group label falls back to the region pkey.
"""

import os
import shutil
import sqlite3

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


LEAF_ATTRS = {'pkey', 'caption', 'child_count', 'treeIdentifier'}


def _root(result):
    return result['root']


def _leaves(bag):
    found = {}

    def collect(node):
        if not node.attr.get('child_count'):
            found[node.attr['pkey']] = node
    bag.walk(collect)
    return found


def _states(db, where=None, **kwargs):
    return db.table('invc.state').query(columns='$code,$region_code,@region_code.name AS region_name',
                                        where=where, **kwargs).fetch()


class TestGroupedByForeignKey:

    def test_leaves_grouped_under_their_fk(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(hierarchical='$region_code')
        expected = {}
        for r in _states(db_sqlite):
            expected.setdefault(r['region_code'], set()).add(r['code'])
        got = {n.attr['hierarchical_value']: {c.attr['pkey'] for c in n.value}
               for n in _root(result)}
        assert got == expected

    def test_group_nodes_count_their_children_and_have_no_pkey(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(hierarchical='$region_code')
        for n in _root(result):
            assert n.attr['child_count'] == len(n.value)
            assert 'pkey' not in n.attr

    def test_leaves_carry_only_pkey_and_caption(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(hierarchical='$region_code')
        for leaf in _leaves(_root(result)).values():
            assert set(leaf.attr) == LEAF_ATTRS
            assert leaf.attr['child_count'] == 0
            assert leaf.attr['treeIdentifier'] == leaf.attr['pkey']
            assert leaf.attr['caption'] == leaf.attr['pkey']

    def test_leaves_of_a_table_with_secrets_leave_them_out(self, db_sqlite):
        result = db_sqlite.table('adm.user').getHierarchicalData(hierarchical='$group_code')
        leaves = _leaves(_root(result))
        assert leaves
        for leaf in leaves.values():
            assert set(leaf.attr) == LEAF_ATTRS

    def test_condition_reaches_the_query(self, db_sqlite):
        some_region = _states(db_sqlite)[0]['region_code']
        result = db_sqlite.table('invc.state').getHierarchicalData(hierarchical='$region_code',
                                                                   condition='$region_code=:rc',
                                                                   condition_rc=some_region)
        assert [n.attr['hierarchical_value'] for n in _root(result)] == [some_region]
        expected = {r['code'] for r in _states(db_sqlite, where='$region_code=:rc', rc=some_region)}
        assert set(_leaves(_root(result))) == expected


class TestGroupedOnSeveralLevels:

    def test_two_levels_with_a_relation_path(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(
            hierarchical='@region_code.name,$region_code')
        for outer in _root(result):
            assert outer.attr['caption'] == outer.attr['hierarchical_value']
            for inner in outer.value:
                states = _states(db_sqlite, where='$region_code=:rc',
                                 rc=inner.attr['hierarchical_value'])
                assert {r['region_name'] for r in states} == {outer.attr['hierarchical_value']}
                assert {c.attr['pkey'] for c in inner.value} == {r['code'] for r in states}
        assert set(_leaves(_root(result))) == {r['code'] for r in _states(db_sqlite)}

    def test_requested_columns_reach_the_leaves(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(
            hierarchical='$region_code', columns='$name,@region_code.name AS region_name')
        for leaf in _leaves(_root(result)).values():
            assert set(leaf.attr) == LEAF_ATTRS | {'name', 'region_name'}
            assert leaf.attr['region_name']


class TestLabels:

    CODES = ('Q.Z', 'Q_Z')

    def test_dots_and_underscores_stay_apart(self, db_sqlite):
        tbl = db_sqlite.table('invc.state')
        region = _states(db_sqlite)[0]['region_code']
        for code in self.CODES:
            tbl.insert(dict(code=code, name=code, region_code=region))
        db_sqlite.commit()
        try:
            by_region = tbl.getHierarchicalData(hierarchical='$region_code')
            group = [n for n in _root(by_region) if n.attr['hierarchical_value'] == region][0]
            assert set(self.CODES) <= {n.attr['pkey'] for n in group.value}
            by_code = tbl.getHierarchicalData(hierarchical='$code')
            groups = {n.attr['hierarchical_value']: n for n in _root(by_code)}
            for code in self.CODES:
                assert [c.attr['pkey'] for c in groups[code].value] == [code]
        finally:
            tbl.deleteSelection(where='$code IN :codes', codes=list(self.CODES))
            db_sqlite.commit()


class TestDbstore:

    def test_tree_reads_the_requested_store(self, db_sqlite, sqlite_temp_dir, tmp_path):
        for name in os.listdir(sqlite_temp_dir):
            shutil.copy(os.path.join(sqlite_temp_dir, name), tmp_path / name)
        dropped = _states(db_sqlite)[0]['region_code']
        with sqlite3.connect(str(tmp_path / 'invc.db')) as conn:
            conn.execute('DELETE FROM invc_state WHERE region_code=?', (dropped,))
        db_sqlite.stores_handler.add_auxstore('hgrouped_b', dbattr=dict(dbname=str(tmp_path / 'testing')))
        tbl = db_sqlite.table('invc.state')
        main_regions = {n.attr['hierarchical_value']
                        for n in _root(tbl.getHierarchicalData(hierarchical='$region_code'))}
        store_regions = {n.attr['hierarchical_value']
                         for n in _root(tbl.getHierarchicalData(hierarchical='$region_code',
                                                                dbstore='hgrouped_b'))}
        assert dropped in main_regions
        assert store_regions == main_regions - {dropped}
