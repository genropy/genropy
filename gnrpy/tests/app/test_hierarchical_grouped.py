"""Tree data of a flat table grouped by some of its fields
(TableBase.getHierarchicalData with ``hierarchical``).

Uses the shared test_invoice fixture from this directory's conftest:
``invc.state.region_code`` points to the flat ``invc.region``, which has
no caption_field, so its group label falls back to the region pkey.
"""

import os
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqltable import GnrSqlStandardException

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


RESTRICTED = 'hg_restricted'
NO_REGION = 'hg_no_region'
ALLOWED = 'hg_allowed'


def _forbid(db, user_group, table, *columns):
    data = Bag()
    for colname in columns:
        data.setItem('cols_permission.%s' % colname, None, forbidden=True)
    db.table('adm.user_config').insert(dict(user_group=user_group, username=None, pkgid=None,
                                            tblid=table, data=data))


@pytest.fixture(scope='module')
def perm_db(db_sqlite):
    db = db_sqlite
    for code in (RESTRICTED, NO_REGION, ALLOWED):
        db.table('adm.group').insert(dict(code=code, description=code))
    _forbid(db, RESTRICTED, 'invc.state', 'name')
    _forbid(db, RESTRICTED, 'invc.region', 'name')
    _forbid(db, NO_REGION, 'invc.state', 'region_code')
    db.commit()
    return db


def _as_group(db, monkeypatch, user_group, **kwargs):
    page = SimpleNamespace(db=db, permissionPars=dict(user=None, user_group=user_group))
    monkeypatch.setattr(db.application, 'site', SimpleNamespace(currentPage=page), raising=False)
    return db.table('invc.state').getHierarchicalData(**kwargs)


def _values(bag):
    found = set()

    def collect(node):
        found.update(v for v in node.attr.values() if isinstance(v, str))
    bag.walk(collect)
    return found


def _names(db):
    rows = db.table('invc.state').query(columns='$code,$name,$region_code,@region_code.name AS region_name').fetch()
    names = {r['name'] for r in rows} | {r['region_name'] for r in rows}
    return names - {r['code'] for r in rows} - {r['region_code'] for r in rows}


class TestPermittedProjection:

    def test_restricted_user_gets_no_forbidden_value(self, perm_db, monkeypatch):
        result = _as_group(perm_db, monkeypatch, RESTRICTED, hierarchical='$region_code',
                           columns='$name,@region_code.name AS region_name')
        for leaf in _leaves(_root(result)).values():
            assert set(leaf.attr) == LEAF_ATTRS
        assert not _values(_root(result)) & _names(perm_db)

    def test_allowed_user_gets_the_requested_columns(self, perm_db, monkeypatch):
        result = _as_group(perm_db, monkeypatch, ALLOWED, hierarchical='$region_code',
                           columns='$name,@region_code.name AS region_name')
        for leaf in _leaves(_root(result)).values():
            assert set(leaf.attr) == LEAF_ATTRS | {'name', 'region_name'}

    @pytest.mark.parametrize('kwargs', [
        dict(hierarchical='$region_code', caption_field='name'),
        dict(hierarchical='$region_code', caption_field='@region_code.name'),
        dict(hierarchical='@region_code.name'),
    ])
    def test_forbidden_caption_or_group_is_refused(self, perm_db, monkeypatch, kwargs):
        with pytest.raises(GnrSqlStandardException):
            _as_group(perm_db, monkeypatch, RESTRICTED, **kwargs)
        result = _as_group(perm_db, monkeypatch, ALLOWED, **kwargs)
        assert _values(_root(result)) & _names(perm_db)

    def test_a_forbidden_relation_hides_what_lies_beyond_it(self, perm_db, monkeypatch):
        result = _as_group(perm_db, monkeypatch, NO_REGION, hierarchical='$code',
                           columns='@region_code.name AS region_name')
        for leaf in _leaves(_root(result)).values():
            assert set(leaf.attr) == LEAF_ATTRS
        with pytest.raises(GnrSqlStandardException):
            _as_group(perm_db, monkeypatch, NO_REGION, hierarchical='@region_code.name')

    @pytest.mark.parametrize('kwargs', [
        dict(hierarchical='$region_code', columns='*'),
        dict(hierarchical='$region_code', columns="$code || $name AS label"),
        dict(hierarchical='$region_code', caption_field="upper($name)"),
        dict(hierarchical="coalesce($region_code,'')"),
    ])
    def test_expressions_are_refused(self, perm_db, monkeypatch, kwargs):
        with pytest.raises(GnrSqlStandardException):
            _as_group(perm_db, monkeypatch, ALLOWED, **kwargs)
