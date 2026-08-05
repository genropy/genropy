# -*- coding: utf-8 -*-

"""Test page for onLoading/onSaving grouplet hooks: end-to-end validation
of data transformation during load and save in GroupletForm with Item store.

The PaymentData grouplet defines:
- onLoading: wraps PaymentDetail children (0, 1, ...) into BagGrid format (r_0, r_1, ...)
- onSaving: unwraps BagGrid format back to flat numbered children

Test flow: load initial data -> verify grid display -> edit -> save -> check raw data"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def _sample_general_data(self):
        """Sample general document data structure"""
        data = Bag()
        data['DocumentType'] = 'TD01'
        data['Currency'] = 'EUR'
        data['Date'] = '2024-01-15::D'
        data['Number'] = '2024/001'
        data['TotalDocumentAmount'] = 1750.00
        return data

    def _sample_payment_data(self):
        """Sample payment data structure with duplicate PaymentDetail labels"""
        data = Bag()
        data['PaymentTerms'] = 'TP02'
        data.addItem('PaymentDetail', Bag(dict(
            PaymentMethod='MP05',
            PaymentDueDate='2024-01-30::D',
            PaymentAmount=1000.00
        )))
        data.addItem('PaymentDetail', Bag(dict(
            PaymentMethod='MP01',
            PaymentDueDate='2024-02-28::D',
            PaymentAmount=500.00
        )))
        data.addItem('PaymentDetail', Bag(dict(
            PaymentMethod='MP08',
            PaymentDueDate='2024-03-31::D',
            PaymentAmount=250.00
        )))
        return data

    def test_1_transform_panel(self, pane):
        """GroupletPanel with transforms grouplets: select PaymentData to see
        onLoading transform flat data into BagGrid rows, edit, then verify
        onSaving restores flat structure"""
        pane.data('.data.general_data', self._sample_general_data())
        pane.data('.data.payment_data', self._sample_payment_data())
        bc = pane.borderContainer(height='500px', border='1px solid silver')
        bc.groupletPanel(
            topic='transforms',
            value='^.data',
            frameCode='transform_panel',
            region='center')
