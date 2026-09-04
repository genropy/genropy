"""Typing of X columns in the selection output (issue #1197).

``out_selection`` feeds app.dbSelect: node attributes travel to the client as
plain strings, so an X column has to carry the ``::X`` suffix or the client
rebuilds it as text instead of a Bag.
"""

import pytest

from gnr.core.gnrbag import Bag

from core.common import BaseGnrTest

# A value whose serialization holds more than one ':', the shape that broke
# loadTemplate in the original report.
DETAILS = Bag(dict(link='http://example.com/a:b'))


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def product_pkey(db_sqlite):
    tbl = db_sqlite.table('invc.product')
    rec = dict(
        id=tbl.newPkeyValue(),
        code='X1197',
        description='Product with an X column',
        details=DETAILS,
    )
    tbl.insert(rec)
    db_sqlite.commit()
    return rec['id']


def _selection(db, pkey):
    return db.table('invc.product').query(
        columns='$id,$description,$details',
        where='$id = :pk', pk=pkey,
    ).selection()


def test_out_selection_types_x_column(db_sqlite, product_pkey):
    result = _selection(db_sqlite, product_pkey).output('selection')
    attr = result.nodes[0].attr
    assert attr['details'].endswith('::X')
    assert Bag(attr['details'][:-3])['link'] == 'http://example.com/a:b'


def test_out_selection_leaves_other_columns_untyped(db_sqlite, product_pkey):
    result = _selection(db_sqlite, product_pkey).output('selection')
    attr = result.nodes[0].attr
    assert attr['description'] == 'Product with an X column'


def test_typed_attributes_skips_empty_values(db_sqlite, product_pkey):
    selection = _selection(db_sqlite, product_pkey)
    attributes = selection.typedAttributes(dict(details=None, description='x'))
    assert attributes['details'] is None
    assert attributes['description'] == 'x'
