"""groupletGrid: griglia di grouplet ripetute, una per ogni riga della Bag.

API base:
  pane.groupletGrid(storepath='.lines',
                    resource='invoice_row',  # oppure handler=callable
                    cols=3,                  # max colonne (default 1)
                    min_width='320px',       # larghezza minima blocchetto
                    addEnabled=True, removeEnabled=True,
                    defaultRow=dict(qty=1), emptyMessage='!!Niente righe')

Comportamento responsive:
  - cols=1 (default) → un blocchetto per riga, niente CSS-grid.
  - cols>1 + min_width → CSS-grid con `repeat(auto-fill, minmax(min_width, 1fr))`,
    cap a `cols` colonne. Re-flow automatico stringendo il viewport.

Stile blocchetto (.grouplet_grid_row):
  - bordo + radius + padding (token design system)
  - hover: background-alt
  - :focus-within (un widget interno ha focus): bordo accent + soft glow
  - .selected (click sul blocchetto, gestito da gridController.selectRow):
    bordo accent + background-alt persistente
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_1_smoke(self, pane):
        """3 righe pre-caricate, single-column (cols=1, no responsive).

        Verifica baseline: i blocchetti sono stack verticali con bordo
        e radius. Hover, focus-within, click → .selected funzionano.
        Add/Del passano dal flusso "double-mutation" (data Bag + src Bag).
        """
        rows = Bag()
        rows.setItem('r_001', Bag(dict(product='Apples',
                                       qty=10, price=2.50)))
        rows.setItem('r_002', Bag(dict(product='Bread',
                                       qty=2, price=1.20)))
        rows.setItem('r_003', Bag(dict(product='Coffee',
                                       qty=1, price=12.00)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 1: smoke 3 righe (single-column, blocchetti card)',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          addEnabled=True, removeEnabled=True)

    def test_2_empty(self, pane):
        """Bag vuota + defaultRow.

        Card "empty state" visibile finché la Bag è vuota; il primo +Add
        lo nasconde e inserisce la riga con i defaultRow applicati.
        """
        pane.data('.invoice_lines', Bag())
        pane.div('Test 2: empty state, defaultRow={qty:1,price:0}',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(
            storepath='.invoice_lines',
            resource='invoice_row',
            addEnabled=True, removeEnabled=True,
            emptyMessage='!!Nessuna riga. Clicca + Add row per aggiungerne una.',
            defaultRow=dict(qty=1, price=0))

    def test_3_handler(self, pane):
        """handler= come callable (no resource).

        Stampa minimale ad-hoc invece di una resource grouplet su disco.
        Usa lo `handler=self.simple_row_handler` per rendere chiaro che
        il framework accetta sia la stringa che il riferimento al metodo.
        """
        pane.data('.lines', Bag())
        pane.div('Test 3: handler=callable (no resource su disco)',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.lines',
                          handler=self.simple_row_handler,
                          addEnabled=True, removeEnabled=True)

    @public_method
    def simple_row_handler(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='4px')
        fb.textbox(value='^.label', lbl='Label', width='100%')
        fb.numberTextBox(value='^.qty', lbl='Qty', width='5em')

    def test_4_excel_grid(self, pane):
        """Excel-style: blocchetti compatti in griglia responsive.

        Usa il grouplet `excel_row` (4 widget inline, no label, solo placeholder).
        cols=4 + min_width='400px' → su monitor wide vedi fino a 4 colonne,
        restringendo il viewport vedi reflow a 3, 2, 1 colonne.
        Stato .selected utile per individuare la riga attiva.
        """
        rows = Bag()
        for i, (prod, qty, price) in enumerate([
            ('Apples', 10, 2.50), ('Bread', 2, 1.20),
            ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
            ('Eggs', 12, 0.30), ('Flour', 3, 2.10),
            ('Grapes', 4, 3.40), ('Honey', 1, 8.00),
        ], start=1):
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        pane.data('.lines', rows)
        pane.div('Test 4: excel-style, cols=4, min_width=400px (responsive)',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.lines',
                          resource='excel_row',
                          cols=4, min_width='400px',
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(qty=1, price=0))

    def test_5_responsive_invoice(self, pane):
        """Invoice_row in griglia responsive 3 colonne.

        cols=3 + min_width='340px': monitor wide → 3 colonne,
        tablet → 2, mobile → 1. Il blocchetto invoice_row ha label
        sopra ogni campo, più "denso" del test_4.
        """
        rows = Bag()
        for i, (prod, qty, price) in enumerate([
            ('Apples', 10, 2.50), ('Bread', 2, 1.20),
            ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
            ('Eggs', 12, 0.30), ('Flour', 3, 2.10),
        ], start=1):
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 5: invoice_row, cols=3, min_width=340px (responsive)',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          cols=3, min_width='300px',
                          addEnabled=True, removeEnabled=True)
