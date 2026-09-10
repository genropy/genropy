"""Optimistic-lock merge test of writeRecordCluster (issue #1287).

The changeSet a form sends back can carry a virtual column: it is absent
from the record ``writeRecordCluster`` reloads for the comparison, so it
used to read as ``None`` and be reported as modified by another user.
"""

import pytest

from core.common import BaseGnrTest

from gnr.core.gnrbag import Bag


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def changeset(**fields):
    """A main changeSet as the client sends it: value plus loaded oldValue."""
    result = Bag()
    for fname, (value, oldValue) in fields.items():
        result.setItem(fname, value, dict(oldValue=oldValue))
    return result


class TestWriteRecordClusterMerge:

    def customer(self, db):
        """A committed customer, with the pkey and the virtual values it has."""
        tblobj = db.table('invc.customer')
        record = tblobj.newrecord(
            account_name='Merge Test', street_address='1 Test Road',
            suburb='Testville', notes='before',
        )
        tblobj.insert(record)
        db.commit()
        return tblobj, record['id']

    def test_virtual_column_is_not_a_conflict(self, db_sqlite):
        # no lastTS in the cluster arms testForMerge (crud.py:543); the
        # virtual fields carry the value the form loaded, unchanged
        tblobj, pkey = self.customer(db_sqlite)
        tblobj.writeRecordCluster(
            changeset(notes=('after', 'before'),
                      has_invoices=(False, False),
                      full_address=('1 Test Road, Testville',
                                    '1 Test Road, Testville'),
                      state_name=('Nowhere', 'Nowhere')),
            dict(_pkey=pkey),
        )
        db_sqlite.commit()
        assert tblobj.record(pkey).output('dict')['notes'] == 'after'

    def test_physical_column_still_conflicts(self, db_sqlite):
        tblobj, pkey = self.customer(db_sqlite)
        with pytest.raises(Exception) as err:
            tblobj.writeRecordCluster(
                changeset(account_name=('Mine', 'Stale Value')),
                dict(_pkey=pkey),
            )
        assert 'Incompatible changes' in str(err.value)
        assert 'account_name' in str(err.value)
        db_sqlite.rollback()
        assert tblobj.record(pkey).output('dict')['account_name'] == 'Merge Test'
