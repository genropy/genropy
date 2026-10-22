"""groupletGrid copy and paste of rows.

  Copy, in a row's kebab, in the bar of the selected rows, or Cmd/Ctrl+C
  with rows selected and no text field focused, puts the rows in the
  clipboard as tab-separated text under a header naming the columns.
  Paste a block of rows:
    - in the blank row (phantom or entry): the rows go to the tail;
    - in a field of a row: the rows go after that row;
    - a single value pastes into the field as usual.
  The header places the columns by name, wherever the paste lands; a column
  no field takes (a formula) is skipped. The text pastes into a spreadsheet
  split in columns, and back from one.

  A plain click selects one row, Cmd/Ctrl/Shift-click several (ticked when
  the rows have checkboxes); Cmd/Ctrl+C copies the selected row or rows,
  also from a field with no text selected.

  test_01_struct  — a grid with a checkbox column among the others; turn
                    the row checkboxes, the trash (delitem) and the copy
                    button (copyitem) on and off above it: the trash, the
                    copy and the kebab line up at the end of the row.
  test_02_cards   — cards: their chrome band holds the checkbox and the
                    kebab (Copy, Delete in red); drag a card by its band. Pick the band's side and the card
                    width above the grid; with the corner chrome the copy
                    button sits left of the trash.
  test_03_entry   — one-line rows edited in the entry row.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_struct(self, pane):
        """Copy rows of a grid and paste them in the blank row or after a row"""
        rows = Bag()
        for i, (item, qty, bought, price) in enumerate((('Milk', 2, True, 1.4),
                                                        ('Bread', 1, False, 2.2),
                                                        ('Apples', 6, False, 0.55))):
            rows.setItem('r_%s' % i, Bag(dict(item=item, qty=qty, bought=bought,
                                              unit_price=price)))
        pane.data('.shopping', rows)
        pane.data('.rowCheckbox', True)
        pane.data('.delitem', True)
        pane.data('.copyitem', True)
        bar = pane.div(display='flex', gap='1em', margin_bottom='8px')
        bar.checkbox(value='^.rowCheckbox', label='Checkboxes')
        bar.checkbox(value='^.delitem', label='Delete button')
        bar.checkbox(value='^.copyitem', label='Copy button')
        pane.div(min_height='1px').remote('structCase', rowCheckbox='^.rowCheckbox',
                                          delitem='^.delitem', copyitem='^.copyitem')

    def remote_structCase(self, pane, rowCheckbox=None, delitem=None, copyitem=None, **kwargs):
        def struct(struct):
            r = struct.view().rows()
            r.cell('item', name='Item', width='100%', edit=True)
            r.cell('qty', name='Qty', width='5em', dtype='L', edit=True)
            r.cell('bought', name='Bought', width='5em', dtype='B', edit=True)
            r.cell('unit_price', name='Unit price', width='7em', dtype='N',
                   edit=True, format='#,###.00')
            r.cell('line_total', name='Line total', width='8em', dtype='N',
                   formula='qty*unit_price', format='#,###.00')

        pane.groupletGrid(storepath='.shopping', struct=struct,
                          nodeId='cp_struct', additem='phantom',
                          delitem=bool(delitem), copyitem=bool(copyitem), editmenu=True,
                          rowCheckbox=rowCheckbox,
                          selectionmenu=dict(copy=True, delete=True),
                          defaultRow=dict(bought=False, qty=1, unit_price=0))

    def test_02_cards(self, pane):
        """Copy cards and paste them as new cards"""
        contacts = Bag()
        for i, (name, role, phone) in enumerate((('Alice', 'Producer', '02 1234'),
                                                 ('Bruno', 'Director', '06 5678'),
                                                 ('Carla', 'Editor', ''))):
            contacts.setItem('r_%s' % i, Bag(dict(name=name, role=role, phone=phone)))
        pane.data('.contacts', contacts)
        pane.data('.chromeSide', 'top')
        pane.data('.min_width', '18em')
        pane.data('.copyitem', True)
        bar = pane.div(display='flex', gap='1em', margin_bottom='8px')
        bar.filteringSelect(value='^.chromeSide', lbl='Band',
                            values='top:Top,left:Left,right:Right,none:None (corner chrome)')
        bar.filteringSelect(value='^.min_width', lbl='Card width',
                            values='12em:Narrow,18em:Medium,36em:Wide')
        bar.checkbox(value='^.copyitem', label='Copy button')
        pane.div(min_height='1px').remote('cardsCase', chromeSide='^.chromeSide',
                                          min_width='^.min_width', copyitem='^.copyitem')

    def remote_cardsCase(self, pane, chromeSide=None, min_width=None, copyitem=None, **kwargs):
        pane.groupletGrid(storepath='.contacts', handler=self.contact_card,
                          nodeId='cp_cards', cols=4, min_width=min_width,
                          chromeSide=False if chromeSide == 'none' else chromeSide,
                          rowCheckbox=True, collapsible=True, copyitem=bool(copyitem),
                          collapsedTemplate='$name ($role)',
                          defaultRow=dict(name='', role='', phone=''))

    def test_03_entry(self, pane):
        """Copy one-line rows and paste them in the entry row"""
        rows = Bag()
        for i, (description, amount) in enumerate((('Body', 900), ('Lenses', 450),
                                                   ('Tripod', 120))):
            rows.setItem('d_%s' % i, Bag(dict(description=description, amount=amount)))
        pane.data('.details', rows)
        pane.groupletGrid(storepath='.details', handler=self.detail_entry,
                          nodeId='cp_entry', additem='entry', delitem=True,
                          rowTemplate='<div style="display:flex;gap:1em">'
                                      '<span style="flex:1">$description</span>'
                                      '<span>$amount</span></div>',
                          defaultRow=dict(amount=0))

    @public_method
    def contact_card(self, pane, **kwargs):
        fb = pane.formlet(cols=1)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.role', lbl='Role')
        fb.textbox(value='^.phone', lbl='Phone')

    @public_method
    def detail_entry(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.description', lbl='Description',
                   validate_notnull=True)
        fb.numberTextBox(value='^.amount', lbl='Amount', format='#,##0.00')
