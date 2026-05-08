"""groupletGrid: griglia di grouplet ripetute, una per ogni riga della Bag.

API base:
  pane.groupletGrid(storepath='.lines',
                    resource='invoice_row',  # oppure handler=callable
                    cols=3,                  # max colonne (default 1)
                    min_width='320px',       # larghezza minima blocchetto
                    addEnabled=True, removeEnabled=True,
                    defaultRow=dict(qty=1))

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
                          nodeId='grpgrid_test1',
                          addEnabled=True, removeEnabled=True)

    def test_2_empty(self, pane):
        """Bag vuota + defaultRow.

        Quando la Bag è vuota si vede solo la phantom row '+ Add row'
        (nessuna empty card separata). Cliccando inserisce la prima
        riga con i defaultRow applicati.
        """
        pane.data('.invoice_lines', Bag())
        pane.div('Test 2: empty state, defaultRow={qty:1,price:0}',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(
            storepath='.invoice_lines',
            resource='invoice_row',
            addEnabled=True, removeEnabled=True,
            defaultRow=dict(qty=1, price=0))

    def test_3_todolist(self, pane):
        """handler=callable: mini todolist.

        Esempio "vero" di handler inline: una riga = un to-do (checkbox
        `done` + textbox `text`). Mostra che `handler=` accetta un
        riferimento di metodo invece di una resource grouplet su disco.
        """
        rows = Bag()
        rows.setItem('r_001', Bag(dict(done=False, text='Buy milk')))
        rows.setItem('r_002', Bag(dict(done=True, text='Send report')))
        rows.setItem('r_003', Bag(dict(done=False,
                                       text='Pick up dry cleaning')))
        pane.data('.todos', rows)
        pane.div('Test 3: todolist (handler=callable)',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.todos',
                          handler=self.todo_row_handler,
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(done=False, text=''))

    @public_method
    def todo_row_handler(self, pane, **kwargs):
        # Inline row: a checkbox and a single-line text input.
        # Keep it loose, no labels — todolist row UX.
        row = pane.div(display='flex', align_items='center', gap='0.6em')
        row.checkBox(value='^.done')
        row.textbox(value='^.text', placeholder='!!What needs doing?',
                    width='100%', flex='1')

    def test_4_excel_grid(self, pane):
        """Fakexcel: righe piatte con toolbar in alto.

        height='320px' attiva la cornice (frame mode): il body scrolla
        internamente. La toolbar nello slot `top` resta ancorata in
        cima e contiene `+` (add) e `−` (delete riga selezionata).
        `addEnabled=False, removeEnabled=False` perché in questa
        modalità i comandi vengono dalla toolbar globale, non dal
        kebab inline o dal phantom-row.
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
        pane.div('Test 4: fakexcel — toolbar sticky + righe piatte',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid_id = 'grpgrid_excel'
        topic = f'groupletGrid_{grid_id}_action'
        grid = pane.groupletGrid(storepath='.lines',
                                 resource='excel_row',
                                 _class='gg-flat-rows',
                                 height='320px',
                                 nodeId=grid_id,
                                 addEnabled=False, removeEnabled=False,
                                 defaultRow=dict(qty=1, price=0))
        toolbar = grid.top.div(_class='gg-excel-toolbar',
                               display='flex', align_items='center',
                               gap='0.4em', padding='0.4em 0.6em',
                               border_bottom='1px solid var(--border-color, #e5e7eb)',
                               background='var(--surface-alt, #f9fafb)')
        toolbar.div('!!Items', font_weight='600', flex='1',
                    color='var(--text-secondary, #6b7280)',
                    font_size='0.9em')
        toolbar.lightButton(
            '+',
            _class='gg-toolbar-btn',
            tip='!!Add row',
            action=f"genro.publish('{topic}', {{action:'add'}});")
        toolbar.lightButton(
            '−',
            _class='gg-toolbar-btn',
            tip='!!Delete selected row',
            action=f"genro.publish('{topic}', {{action:'delete'}});")

    def test_6_framed(self, pane):
        """Frame mode: scroll interno + bottom slot popolato.

        height=400px attiva la cornice: il body scrolla internamente,
        il bottom slot resta ancorato in fondo (non scrolla col body).
        Il bottom è popolato via `grid.bottom.div(...)`: prima del
        controller bootstrap il container ha autoslot=top,bottom,left,right
        e il magic __getattr__ materializza lo slot solo se ci scrivi dentro.
        """
        rows = Bag()
        for i in range(1, 31):
            rows.setItem(f'r_{i:03d}',
                         Bag(dict(product=f'Item {i}',
                                  qty=i, price=i * 1.5)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 6: framed (height=400px) — bottom slot ancorato',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid = pane.groupletGrid(storepath='.invoice_lines',
                                 resource='invoice_row',
                                 height='400px',
                                 addEnabled=True, removeEnabled=True)
        grid.bottom.div('!!Total: 30 rows',
                        _class='gg-footer-info',
                        padding='6px 12px',
                        border_top='1px solid var(--border-color, #e5e7eb)',
                        background='var(--surface-alt, #f9fafb)',
                        font_size='0.9em',
                        color='var(--text-secondary, #6b7280)')

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
                          addEnabled=True, removeEnabled=True,
                          dragCode='test2_invoice')
