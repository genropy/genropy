# -*- coding: utf-8 -*-

"""groupletGrid card mode: `formulas=` and the `totals=` band.

Every test binds the same document rows (quantity, VAT-inclusive price, VAT
rate): the row formulas compute the line total and its net, the band sums them
and derives the VAT from the two totals.
"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

FORMULAS = dict(totale_riga='quantita*prezzo_unitario',
                netto_riga='totale_riga/(1+(aliquota_iva==null?4:aliquota_iva)/100)')
TOTALS = [dict(field='netto_riga', label='Net'),
          dict(name='iva', label='VAT', formula='totale_riga-netto_riga'),
          dict(field='totale_riga', label='Total', highlight=True)]
RIGHE = (('The upstairs room', 3, 16.5, 4),
         ('Frog song', 2, 12.9, 4),
         ('Board game', 1, 39.9, 22),
         ('No rate: counts as a book', 1, 10.4, None))


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_1_document_totals(self, pane):
        """Row formulas and a totals band: edit a quantity, a price or a rate"""
        pane.data('.righe', self._righe())
        self._grid(pane, '.righe')

    def test_2_hidden_band(self, pane):
        """totals_hidden: the band follows a flag outside the grid"""
        pane.data('.righe', self._righe())
        pane.data('.vendita', True)
        pane.checkbox(value='^.vendita', label='Sale document (show the money)')
        self._grid(pane, '.righe', totals_hidden='^.vendita?=!#v')

    def test_3_framed(self, pane):
        """height=: the body scrolls, the band stays at the foot"""
        pane.data('.righe', self._righe(times=6))
        self._grid(pane, '.righe', height='320px')

    def test_4_sticky(self, pane):
        """totals_sticky: unframed grid in a scrolling box, band pinned"""
        pane.data('.righe', self._righe(times=6))
        box = pane.div(height='320px', overflow='auto',
                       border='1px solid var(--border-color, #ddd)')
        self._grid(box, '.righe', totals_sticky=True)

    def test_5_theme_tokens(self, pane):
        """--totals-*: a theme (here an ancestor) recolours the band"""
        pane.data('.righe', self._righe())
        box = pane.div(style='--totals-bg:#1B1F3B;--totals-text:#FBF7F0;'
                             '--totals-highlight:#E8A33D;'
                             '--totals-marker:transparent;')
        self._grid(box, '.righe')

    def test_6_struct_unchanged(self, pane):
        """struct= mode keeps its formula column and aligned totalize footer"""
        pane.data('.righe', self._righe())

        def struct(struct):
            r = struct.view().rows()
            r.cell('descrizione', name='Item', width='100%', edit=True)
            r.cell('quantita', name='Qty', width='5em', dtype='L', edit=True)
            r.cell('prezzo_unitario', name='Price', width='7em', dtype='N',
                   edit=True, format='#,###.00')
            r.cell('totale_riga', name='Line total', width='8em', dtype='N',
                   formula='quantita*prezzo_unitario', totalize=True,
                   format='#,###.00')

        pane.groupletGrid(storepath='.righe', struct=struct, additem=False)

    def _grid(self, pane, storepath, **kwargs):
        pane.groupletGrid(storepath=storepath, handler=self.rigaDocumento,
                          cols=1, formulas=FORMULAS, totals=TOTALS,
                          totals_format='#,###.00',
                          defaultRow=dict(quantita=1, prezzo_unitario=0,
                                          aliquota_iva=4),
                          **kwargs)

    def _righe(self, times=1):
        righe = Bag()
        for n in range(times):
            for i, (descrizione, quantita, prezzo, aliquota) in enumerate(RIGHE):
                righe.setItem('r_%02d_%d' % (n, i),
                              Bag(dict(descrizione=descrizione,
                                       quantita=quantita,
                                       prezzo_unitario=prezzo,
                                       aliquota_iva=aliquota)))
        return righe

    @public_method
    def rigaDocumento(self, pane, **kwargs):
        fb = pane.formlet(cols=5)
        fb.textbox(value='^.descrizione', lbl='Item', colspan=2)
        fb.numberTextBox(value='^.quantita', lbl='Qty', dtype='L')
        fb.numberTextBox(value='^.prezzo_unitario', lbl='Price',
                         format='#,###.00')
        fb.numberTextBox(value='^.aliquota_iva', lbl='VAT %')
        fb.div('^.netto_riga', lbl='Net', format='#,###.00', colspan=2)
        fb.div('^.totale_riga', lbl='Line total', format='#,###.00',
               colspan=3)
