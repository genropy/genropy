# -*- coding: utf-8 -*-

"""Test page for onLoading/onSaving grouplet hooks: end-to-end validation
of data transformation during load and save in GroupletForm with Item store.

The DatiPagamento grouplet defines:
- onLoading: wraps DettaglioPagamento children (0, 1, ...) into BagGrid format (r_0, r_1, ...)
- onSaving: unwraps BagGrid format back to flat numbered children

Test flow: load initial data -> verify grid display -> edit -> save -> check raw data"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def _sample_dati_generali(self):
        """FatturaPA-like DatiGeneraliDocumento structure"""
        data = Bag()
        data['TipoDocumento'] = 'TD01'
        data['Divisa'] = 'EUR'
        data['Data'] = '2024-01-15::D'
        data['Numero'] = '2024/001'
        data['ImportoTotaleDocumento'] = 1750.00
        return data

    def _sample_dati_pagamento(self):
        """FatturaPA-like DatiPagamento structure with duplicate DettaglioPagamento labels"""
        data = Bag()
        data['CondizioniPagamento'] = 'TP02'
        data.addItem('DettaglioPagamento', Bag(dict(
            ModalitaPagamento='MP05',
            DataScadenzaPagamento='2024-01-30::D',
            ImportoPagamento=1000.00
        )))
        data.addItem('DettaglioPagamento', Bag(dict(
            ModalitaPagamento='MP01',
            DataScadenzaPagamento='2024-02-28::D',
            ImportoPagamento=500.00
        )))
        data.addItem('DettaglioPagamento', Bag(dict(
            ModalitaPagamento='MP08',
            DataScadenzaPagamento='2024-03-31::D',
            ImportoPagamento=250.00
        )))
        return data

    def test_1_transform_panel(self, pane):
        """GroupletPanel with transforms grouplets: select DatiPagamento to see
        onLoading transform flat data into BagGrid rows, edit, then verify
        onSaving restores flat structure"""
        pane.data('.data.dati_generali', self._sample_dati_generali())
        pane.data('.data.dati_pagamento', self._sample_dati_pagamento())
        bc = pane.borderContainer(height='500px', border='1px solid silver')
        bc.groupletPanel(
            topic='transforms',
            value='^.data',
            frameCode='transform_panel',
            region='center')

