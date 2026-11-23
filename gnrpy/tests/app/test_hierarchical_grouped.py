"""Tree data of a flat table grouped by some of its fields
(TableBase.getHierarchicalData with ``hierarchical``).

Uses the shared test_invoice fixture from this directory's conftest:
``invc.state.region_code`` points to the flat ``invc.region``, which has
no caption_field, so its group label falls back to the region pkey.
"""

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


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

    def test_leaves_carry_pkey_caption_and_row_columns(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(hierarchical='$region_code')
        group = _root(result).getNodes()[0]
        leaf = group.value.getNodes()[0]
        assert leaf.attr['child_count'] == 0
        assert leaf.attr['treeIdentifier'] == leaf.attr['pkey']
        assert leaf.attr['caption'] == leaf.attr['code']
        assert leaf.attr['region_code'] == group.attr['hierarchical_value']

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

    def test_extra_columns_reach_the_leaves(self, db_sqlite):
        result = db_sqlite.table('invc.state').getHierarchicalData(
            hierarchical='$region_code', columns='*,@region_code.name AS region_name')
        leaf = next(iter(_leaves(_root(result)).values()))
        assert leaf.attr['region_name']
