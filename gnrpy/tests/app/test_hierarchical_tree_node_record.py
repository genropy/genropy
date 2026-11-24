"""Tree nodes of getHierarchicalData must not carry hidden columns to the client.

``_record`` and the attributes of related nodes keep every column the query
selected (``'*'`` by default, which client code relies on), except the system
columns (``__ins_ts``, ``__mod_ts``...) and the columns forbidden to the current
user through ``adm.user_config``.

Three paths are exercised on the test_invoice database:

* ``invc.product_group`` — hierarchical table, ``TableHandlerTreeResolver``;
* ``invc.product_type`` with related ``invc.product`` — the related children
  of the same resolver;
* ``invc.vat_type`` with related ``invc.product`` — a plain table, served by
  ``getHierarchicalDataBag``.
"""

from types import SimpleNamespace

import pytest

from gnr.core.gnrbag import Bag

from core.common import BaseGnrTest


RESTRICTED = 'restricted'
OTHER = 'other'


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _forbid(db, table, *columns):
    data = Bag()
    for colname in columns:
        data.setItem('cols_permission.%s' % colname, None, forbidden=True)
    db.table('adm.user_config').insert(dict(user_group=RESTRICTED, username=None, pkgid=None,
                                            tblid=table, data=data))


@pytest.fixture(scope='module')
def tree_db(db_sqlite):
    db = db_sqlite
    groups = db.table('adm.group')
    for code in (RESTRICTED, OTHER):
        groups.insert(dict(code=code, description=code))
    _forbid(db, 'invc.product_group', 'description')
    _forbid(db, 'invc.product', 'unit_price')
    _forbid(db, 'invc.vat_type', 'vat_rate')
    pg = db.table('invc.product_group')
    root = pg.insert(pg.newrecord(code='A', description='secret root'))
    pg.insert(pg.newrecord(code='B', description='secret child', parent_id=root['id']))
    db.commit()
    return db


def _tree(db, monkeypatch, user_group, table, **kwargs):
    page = SimpleNamespace(db=db, permissionPars=dict(user=None, user_group=user_group))
    monkeypatch.setattr(db.application, 'site', SimpleNamespace(currentPage=page), raising=False)
    return db.table(table).getHierarchicalData(resolved=True, **kwargs)


def _nodes(bag):
    result = []

    def cb(node):
        result.append(node)
    bag.walk(cb, _mode='')
    return result


PRODUCT_GROUP_RECORD = {
    'id', 'pkey', 'parent_id', 'code', 'hierarchical_code', '_parent_h_code',
    '_row_count', 'hierarchical__row_count', '_parent_h__row_count',
    'hierarchical_pkey', '_parent_h_pkey', '_h_count', '_parent_h_count',
    'child_count',
}


class TestTreeResolverRecord:

    def test_restricted_user(self, tree_db, monkeypatch):
        tree = _tree(tree_db, monkeypatch, RESTRICTED, 'invc.product_group')
        root = tree['root.#0']
        root_node = tree.getNode('root.#0')
        child_node = root.getNode('#0')
        assert set(root_node.attr) == {'caption', 'child_count', 'pkey', 'hierarchical_pkey',
                                       'treeIdentifier', '_record'}
        assert set(child_node.attr) == {'caption', 'child_count', 'pkey', 'parent_id',
                                        'hierarchical_pkey', 'treeIdentifier', '_record'}
        assert set(root_node.attr['_record']) == PRODUCT_GROUP_RECORD
        assert set(child_node.attr['_record']) == PRODUCT_GROUP_RECORD
        xml = tree.toXml(unresolved=True, omitUnknownTypes=True)
        assert 'secret root' not in xml
        assert '__ins_ts' not in xml

    def test_allowed_user_keeps_the_columns(self, tree_db, monkeypatch):
        tree = _tree(tree_db, monkeypatch, OTHER, 'invc.product_group')
        record = tree.getNode('root.#0').attr['_record']
        assert set(record) == PRODUCT_GROUP_RECORD | {'description'}
        assert record['description'] == 'secret root'

    def test_explicit_columns_still_reach_the_record(self, tree_db, monkeypatch):
        tree = _tree(tree_db, monkeypatch, RESTRICTED, 'invc.product_group',
                     columns='$id,$hierarchical_pkey,$code')
        assert set(tree.getNode('root.#0').attr['_record']) == {
            'id', 'pkey', 'hierarchical_pkey', 'code', 'child_count'}


class TestRelatedChildren:

    def _related_nodes(self, db, monkeypatch, user_group, table, path):
        tree = _tree(db, monkeypatch, user_group, table,
                     related_table='invc.product', related_path=path)
        related = [n for n in _nodes(tree) if n.attr.get('node_class') == 'tree_related']
        assert related
        return related

    @pytest.mark.parametrize('table,path', [('invc.product_type', '$product_type_id'),
                                            ('invc.vat_type', 'vat_type_code')])
    def test_restricted_user(self, tree_db, monkeypatch, table, path):
        for node in self._related_nodes(tree_db, monkeypatch, RESTRICTED, table, path):
            assert 'unit_price' not in node.attr
            assert not [k for k in node.attr if k.startswith('__')]
            assert 'code' in node.attr

    @pytest.mark.parametrize('table,path', [('invc.product_type', '$product_type_id'),
                                            ('invc.vat_type', 'vat_type_code')])
    def test_allowed_user_keeps_the_columns(self, tree_db, monkeypatch, table, path):
        for node in self._related_nodes(tree_db, monkeypatch, OTHER, table, path):
            assert 'unit_price' in node.attr
            assert not [k for k in node.attr if k.startswith('__')]


class TestHierarchicalDataBagRecord:

    def test_restricted_user(self, tree_db, monkeypatch):
        tree = _tree(tree_db, monkeypatch, RESTRICTED, 'invc.vat_type',
                     related_table='invc.product', related_path='vat_type_code')
        records = [n.attr['_record'] for n in tree['root'].nodes]
        assert records
        for record in records:
            assert set(record) == {'code', 'description', 'pkey'}

    def test_allowed_user_keeps_the_columns(self, tree_db, monkeypatch):
        tree = _tree(tree_db, monkeypatch, OTHER, 'invc.vat_type',
                     related_table='invc.product', related_path='vat_type_code')
        for node in tree['root'].nodes:
            assert set(node.attr['_record']) == {'code', 'description', 'vat_rate', 'pkey'}
