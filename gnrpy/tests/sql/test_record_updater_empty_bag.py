"""recordToUpdate keeps a copy of an empty Bag column in the old record.

An empty Bag is falsy, so it was left shared between the record and the old
record: a change made in place on it was invisible to ``fieldsChanged`` in the
update triggers.
"""

from gnr.core.gnrbag import Bag

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _product_with_empty_details(db):
    tbl = db.table('invc.product')
    pkey = tbl.query(columns='$id', limit=1).fetch()[0]['pkey']
    with tbl.recordToUpdate(pkey) as record:
        record['details'] = Bag()
    db.commit()
    return tbl, pkey


def test_in_place_change_of_an_empty_bag_is_a_change(db_sqlite):
    tbl, pkey = _product_with_empty_details(db_sqlite)
    updater = tbl.recordToUpdate(pkey)
    with updater as record:
        assert isinstance(record['details'], Bag) and not record['details']
        record['details'].setItem('color', 'red')
        assert updater.oldrecord['details'] is not record['details']
        assert tbl.fieldsChanged('details', record, updater.oldrecord)
    db_sqlite.commit()
    assert tbl.record(pkey).output('record')['details']['color'] == 'red'
