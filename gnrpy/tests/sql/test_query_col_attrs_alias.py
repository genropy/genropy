"""Column attributes of an output field renamed with AS.

``SqlQuery._prepColAttrs`` maps an output name back to its source column
through ``compiled.aliasDict``, whose keys are the adapter-translated names
(``"price"``), not the cursor names (``price``). A renamed field carries the
attributes and the permissions of its source column.
"""

import pytest

from gnr.core.gnrbag import Bag

from core.common import BaseGnrTest

RESTRICTED = 'restricted'


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module')
def db(db_sqlite):
    db_sqlite.table('adm.group').insert(dict(code=RESTRICTED, description=RESTRICTED))
    data = Bag()
    data.setItem('cols_permission.unit_price', None, forbidden=True)
    db_sqlite.table('adm.user_config').insert(dict(user_group=RESTRICTED, username=None, pkgid=None,
                                                   tblid='invc.product', data=data))
    db_sqlite.commit()
    return db_sqlite


def _selection(db, columns, user_group=None):
    checkPermissions = dict(user=None, user_group=user_group) if user_group else None
    return db.table('invc.product').query(columns=columns, limit=3,
                                          checkPermissions=checkPermissions).selection()


def test_renamed_column_takes_the_source_attributes(db):
    colAttrs = _selection(db, '$unit_price,$unit_price AS price,$description AS label').colAttrs
    assert colAttrs['price'] == colAttrs['unit_price']
    assert colAttrs['price']['dataType'] == 'N'
    assert colAttrs['label']['label'] == '!!Description'


def test_alias_named_like_another_column_takes_its_source(db):
    colAttrs = _selection(db, '$description AS code').colAttrs
    assert colAttrs['code']['label'] == '!!Description'


def test_renamed_forbidden_column_is_forbidden(db):
    selection = _selection(db, '$code,$unit_price AS price', user_group=RESTRICTED)
    assert selection.colAttrs['price']['user_forbidden'] is True
    assert not selection.colAttrs['code'].get('user_forbidden')
    for node in selection.output('selection').nodes:
        assert 'price' not in node.attr
        assert 'code' in node.attr
