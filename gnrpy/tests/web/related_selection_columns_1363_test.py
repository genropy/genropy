"""Regression tests for issue #1363: ``getRelatedSelection`` dropped the
``columns`` it received and always selected every column of the target table.

Everything runs against a real sqlite instance of ``test_invoice``: the handler
is built with ``__new__`` because ``getRelatedSelection`` reaches the database
only through ``self.db``, which ``GnrBaseProxy.__getattr__`` resolves on the page.
"""

import datetime
from decimal import Decimal

from core.common import BaseGnrAppTest

from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler, related


CUSTOMER_PKEY = 'CUST_1363'

RESOLVER_ATTRIBUTES = {'_pkey', '_relation_value', '_target_fld', '_from_fld',
                       '_resolver_name', '_sqlContextName'}

INVOICES = [('INV_1363_1', 'A0001', Decimal('100.00'), datetime.date(2026, 1, 1)),
            ('INV_1363_2', 'A0002', Decimal('250.50'), datetime.date(2026, 1, 2))]


class _FakePage:
    """The only thing ``getRelatedSelection`` asks of the page is ``db``."""

    def __init__(self, db):
        self.db = db


class TestRelatedSelectionColumns(BaseGnrAppTest):
    app_name = 'test_invoice'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        db = cls.app.db
        db.model.check(applyChanges=True)
        db.table('invc.region').insert(dict(code='R1', name='Region one'))
        db.table('invc.state').insert(dict(code='ST', name='State one',
                                           region_code='R1'))
        db.table('invc.customer_type').insert(dict(code='CT',
                                                   description='Customer type'))
        db.table('invc.payment_type').insert(dict(code='PT',
                                                  description='Payment type'))
        customer_tbl = db.table('invc.customer')
        customer_tbl.insert(customer_tbl.newrecord(
            id=CUSTOMER_PKEY, account_name='Acme', state='ST',
            customer_type_code='CT', payment_type_code='PT'))
        invoice_tbl = db.table('invc.invoice')
        for pkey, inv_number, total, date in INVOICES:
            invoice_tbl.insert(invoice_tbl.newrecord(
                id=pkey, inv_number=inv_number, total=total, date=date,
                customer_id=CUSTOMER_PKEY))
        db.commit()
        cls.handler = GnrWebAppHandler.__new__(GnrWebAppHandler)
        cls.handler.page = _FakePage(db)

    def relatedSelection(self, columns):
        return self.handler.getRelatedSelection(
            from_fld='invc.customer.id',
            target_fld='invc.invoice.customer_id',
            relation_value=CUSTOMER_PKEY,
            columns=columns)

    def test_module_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure
        # the module being exercised is the one in this working tree
        checkout = __file__.rsplit('/gnrpy/tests/', 1)[0]
        assert related.__file__.startswith(checkout + '/')

    def test_only_the_requested_columns_are_returned(self):
        result, resultAttributes = self.relatedSelection('$inv_number,$total')

        assert resultAttributes['totalrows'] == len(INVOICES)
        assert [node.label for node in result] == [row[0] for row in INVOICES]
        for node, (pkey, inv_number, total, _date) in zip(result, INVOICES):
            assert set(node.attr) == RESOLVER_ATTRIBUTES | {'inv_number', 'total'}
            assert node.attr['_pkey'] == pkey
            assert node.attr['inv_number'] == inv_number
            assert node.attr['total'] == total

    def test_no_columns_still_selects_them_all(self):
        result, _resultAttributes = self.relatedSelection('')

        table_columns = set(self.app.db.table('invc.invoice').columns)
        for node in result:
            assert table_columns.issubset(set(node.attr))
