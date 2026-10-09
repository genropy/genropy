"""groupletGrid `additem='phantom'` — the trailing blank row (or card) to type into.

  test_01_phantom_in_form — shopping list inside a memory form. The grid
                            ends with a faded blank row: it is not in the
                            record (the side panel lists the stored rows,
                            the semaphore stays clean) until a value is
                            entered, then it becomes a real row and a new
                            blank row appears below it. Empty a row added
                            here and leave it: it is removed (a loaded row
                            stays, use its ×). Lock the form and the blank
                            row disappears.
  test_02_phantom_empty   — the same grid with no rows at all: the blank
                            row is there from the start, ready to type in.
  test_03_phantom_fill    — `fillParent=True` in a contentPane: header
                            pinned at the top, totals at the bottom, only
                            the rows scroll.
  test_04_phantom_cards   — card layout (`handler=` template): the last
                            card is a dashed blank one; typing in it adds
                            the contact, nested fields included.
  test_05_entry_struct    — `additem='entry'`: an entry row under the
                            header. Enter or its + adds the expense at the
                            tail (scrolled into view) and clears the row;
                            Date and Shop are `keepable`: tick the small
                            square beside them to keep their value for the
                            next entry. Esc clears; an empty Item stops it.
  test_05b_entry_struct_template — the same expenses with `rowTemplate=True`:
                            the rows are the struct read-only, on the same
                            columns; click one to edit it in the entry row.
  Paste, in any phantom or entry row: rows copied from a spreadsheet (TSV)
  or a CSV (`;` or `,`) go to the tail, one row each, columns in field
  order from the field pasted into; a header line naming the columns is
  skipped. Numbers and dates are read as typed (3,20 · 01/10/2026 or ISO).
  test_06_entry_cards     — the same with cards: the entry card sits above
                            the list, Role is `keepable`.
  test_07_entry_template  — `rowTemplate`: the rows are one-line summaries.
                            Click one: it loads in the entry row (tinted,
                            ✓ instead of +), Enter saves it in place, Esc
                            gives up; a new contact being typed is set
                            aside meanwhile and comes back.
"""
import datetime

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    DUPLICATE_ROWS = (
        "var rows = grid.dataStore.getData();"
        "rowKeys.forEach(function(k){"
        "rows.setItem('r_' + genro.time36Id(), rows.getItem(k).deepCopy());});")
    CONTACT_TEMPLATE = (
        '<div style="display:flex;justify-content:space-between;gap:1em">'
        '<b>$name</b><span style="color:var(--text-secondary,#6b7280)">$role</span>'
        '</div>'
        '<div style="font-size:.9em;color:var(--text-secondary,#6b7280)">'
        '$email${ · $extra.phone}</div>')

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_phantom_in_form(self, pane):
        """Type in the faded last row: the row joins the record only then"""
        lines = Bag()
        lines.setItem('r_001', Bag(dict(bought=False, item='Milk',
                                        qty=2, unit_price=1.40)))
        pane.data('.shopping', Bag(dict(title='Weekly shopping',
                                        lines=lines)))
        form = pane.frameForm(frameCode='phantom_form',
                              height='420px', width='100%',
                              datapath='.phantomform',
                              border='1px solid silver')
        form.formStore(storeType='Item', handler='memory',
                       locationpath='.#parent.shopping')
        form.top.slotToolbar('5,*,semaphore,locker,formcommands,5')
        bc = form.center.borderContainer(datapath='.record')
        side = bc.contentPane(region='right', width='170px', padding='10px',
                              border_left='1px solid silver')
        side.div('Rows stored in the record', font_weight='600')
        side.div('^#FORM.lines_count', margin_bottom='6px', font_size='1.6em')
        side.div('^#FORM.lines_dump', font_family='monospace',
                 font_size='12px', white_space='pre')
        bc.dataFormula('#FORM.lines_count', 'lines ? lines.len() : 0',
                       lines='^.lines')
        bc.dataFormula('#FORM.lines_dump',
                       """lines ? lines.getNodes().map(function(n){
                              var r = n.getValue();
                              return n.label + '  ' + (r.getItem('item') || '')
                                     + ' x' + (r.getItem('qty') || '');
                          }).join('\\n') : ''""",
                       lines='^.lines')

        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.lines',
                            struct=self._shopping_struct,
                            nodeId='grpgrid_phantom',
                            additem='phantom',
                            delitem=True,
                            defaultRow=dict(bought=False, qty=1,
                                            unit_price=0))
        bc.dataController('this.form.load()', _onStart=True)

    def test_02_phantom_empty(self, pane):
        """No rows yet: the blank row is the whole grid"""
        pane.div('^.empty_lines?=#v ? #v.len() + " rows stored" : "no rows stored"',
                 margin_bottom='6px')
        pane.groupletGrid(storepath='.empty_lines',
                          struct=self._shopping_struct,
                          nodeId='grpgrid_phantom_empty',
                          additem='phantom',
                          delitem=True,
                          defaultRow=dict(bought=False, qty=1,
                                          unit_price=0))

    def test_03_phantom_fill(self, pane):
        """The grid fills its contentPane: only the rows scroll"""
        catalogue = ['Milk', 'Bread', 'Apples', 'Coffee', 'Pasta', 'Eggs']
        lines = Bag()
        for i in range(1, 31):
            lines.setItem(f'r_{i:03d}',
                          Bag(dict(bought=False,
                                   item=f'{catalogue[i % len(catalogue)]} {i}',
                                   qty=i % 4 + 1, unit_price=1.25)))
        pane.data('.fill_lines', lines)
        self._paste_sample(pane, 'Tea\t2\t3,50\nCake\t1\t12\nJam\t3\t2,20',
                           'Copy, then paste into the blank row\'s Item: '
                           'three rows (Item, Qty, Unit price) are added')
        bc = pane.borderContainer(height='360px', border='1px solid silver')
        bc.contentPane(region='top', padding='6px 10px').div(
            'The center contentPane is 360px tall minus this band: the '
            'header and the totals stay put, the 30 rows scroll between '
            'them.', color='#666', font_style='italic')
        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.fill_lines',
                            struct=self._shopping_struct,
                            nodeId='grpgrid_phantom_fill',
                            fillParent=True,
                            additem='phantom',
                            delitem=True,
                            defaultRow=dict(bought=False, qty=1,
                                            unit_price=0))

    def test_04_phantom_cards(self, pane):
        """Card layout: the dashed last card becomes a contact when typed in"""
        contacts = Bag()
        contacts.setItem('c_001', Bag(dict(name='Mario Rossi', role='Sales',
                                           email='m.rossi@acme.it')))
        pane.data('.contacts', contacts)
        pane.div('^.contacts?=#v ? #v.len() + " contacts stored" : "no contacts stored"',
                 margin_bottom='6px')
        pane.groupletGrid(storepath='.contacts',
                          handler=self.contact_card,
                          nodeId='grpgrid_phantom_cards',
                          cols=3, min_width='200px',
                          additem='phantom',
                          additem_label='!!New contact',
                          delitem=True,
                          defaultRow=dict(role='Sales'))

    def test_05_entry_struct(self, pane):
        """Entry row: Enter adds at the tail, date and shop are keepable"""
        lines = Bag()
        shops = ['Coop', 'Esselunga', 'Pharmacy']
        for i in range(1, 21):
            lines.setItem(f'e_{i:03d}',
                          Bag(dict(date=datetime.date(2026, 9, i),
                                   shop=shops[i % len(shops)],
                                   item=f'Expense {i}', amount=i * 2.5)))
        pane.data('.expenses', lines)
        self._paste_sample(pane,
                           'Date\tShop\tItem\tAmount\n'
                           '01/10/2026\tLidl\tBananas\t3,20\n'
                           '2026-10-02\tCoop\tBread\t1,10\n'
                           '02/10/2026\tPharmacy\tPlasters\t4,90',
                           'Copy (as from a spreadsheet, with its header), '
                           'then paste into the entry row\'s Date')
        bc = pane.borderContainer(height='380px', border='1px solid silver')
        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.expenses',
                            struct=self._expense_struct,
                            nodeId='grpgrid_entry_struct',
                            fillParent=True,
                            additem='entry',
                            additem_label='!!New expense',
                            delitem=True)

    def test_05b_entry_struct_template(self, pane):
        """Struct template rows: click edits on top, the checkboxes select rows for the bar below"""
        lines = Bag()
        shops = ['Coop', 'Esselunga', 'Pharmacy']
        for i in range(1, 21):
            lines.setItem(f'e_{i:03d}',
                          Bag(dict(date=datetime.date(2026, 9, i),
                                   shop=shops[i % len(shops)],
                                   item=f'Expense {i}', amount=i * 2.5)))
        pane.data('.tpl_expenses', lines)
        bc = pane.borderContainer(height='380px', border='1px solid silver')
        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.tpl_expenses',
                            struct=self._expense_struct,
                            nodeId='grpgrid_entry_struct_template',
                            fillParent=True,
                            additem='entry',
                            additem_label='!!New expense',
                            rowTemplate=True,
                            rowCheckbox=True,
                            delitem=True,
                            selectionmenu=dict(
                                delete=True,
                                duplicate=dict(
                                    label='!!Duplicate',
                                    action=self.DUPLICATE_ROWS)))

    def test_06_entry_cards(self, pane):
        """One-line entry on top, contacts side by side below: click one to
        edit it on top, check them to act on several, Role is keepable"""
        contacts = Bag()
        contacts.setItem('c_001', Bag(dict(name='Mario Rossi', role='Sales',
                                           email='m.rossi@acme.it')))
        contacts.setItem('c_002', Bag(dict(name='Elena Blu', role='Support',
                                           email='e.blu@acme.it')))
        pane.data('.entry_contacts', contacts)
        self._paste_sample(pane,
                           'Anna Bianchi;Purchasing;a.bianchi@acme.it;333 111\n'
                           'Luca Verdi;Sales;l.verdi@acme.it;\n'
                           '"Neri, Sara";Support;s.neri@acme.it;333 222',
                           'Copy (a CSV with ;), then paste into the entry '
                           'card\'s Name')
        pane.groupletGrid(storepath='.entry_contacts',
                          handler=self.contact_line,
                          nodeId='grpgrid_entry_cards',
                          cols=3, min_width='200px',
                          additem='entry',
                          additem_label='!!New contact',
                          rowTemplate=self.CONTACT_TEMPLATE,
                          rowCheckbox=True,
                          delitem=True,
                          defaultRow=dict(role='Sales'))

    def test_07_entry_template(self, pane):
        """Template rows: click edits in the entry row, Cmd/Shift+click selects several to delete"""
        contacts = Bag()
        for i, (name, role, email) in enumerate((
                ('Mario Rossi', 'Sales', 'm.rossi@acme.it'),
                ('Anna Bianchi', 'Purchasing', 'a.bianchi@acme.it'),
                ('Luca Verdi', 'Sales', 'l.verdi@acme.it'),
                ('Sara Neri', 'Support', 's.neri@acme.it'),
                ('Paolo Gialli', 'Support', 'p.gialli@acme.it'),
                ('Elena Blu', 'Sales', 'e.blu@acme.it')), start=1):
            contacts.setItem(f'c_{i:03d}', Bag(dict(name=name, role=role,
                                                     email=email)))
        pane.data('.tpl_contacts', contacts)
        bc = pane.borderContainer(height='380px', border='1px solid silver')
        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.tpl_contacts',
                            handler=self.contact_editor,
                            nodeId='grpgrid_entry_template',
                            fillParent=True,
                            additem='entry',
                            additem_label='!!New contact',
                            rowTemplate=self.CONTACT_TEMPLATE,
                            delitem=True,
                            defaultRow=dict(role='Sales'))

    @public_method
    def contact_line(self, pane, **kwargs):
        fb = pane.formlet(cols=4)
        fb.textbox(value='^.name', lbl='Name', validate_notnull=True)
        fb.textbox(value='^.role', lbl='Role', keepable=True)
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.extra.phone', lbl='Phone')

    @public_method
    def contact_editor(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.name', lbl='Name', validate_notnull=True)
        fb.textbox(value='^.role', lbl='Role', keepable=True)
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.extra.phone', lbl='Phone')

    def _expense_struct(self, struct):
        r = struct.view().rows()
        r.cell('date', name='Date', width='8em', dtype='D', edit=True,
               keepable=True)
        r.cell('shop', name='Shop', width='9em', edit=True, keepable=True)
        r.cell('item', name='Item', width='100%',
               edit=True, validate_notnull=True)
        r.cell('amount', name='Amount', width='7em', dtype='N', edit=True,
               format='#,###.00', totalize='.total_amount')

    @public_method
    def contact_card(self, pane, **kwargs):
        fb = pane.formlet(cols=1)
        fb.textbox(value='^.name', lbl='Name', validate_notnull=True)
        fb.textbox(value='^.role', lbl='Role', keepable=True)
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.extra.phone', lbl='Phone')

    def _paste_sample(self, pane, sample, hint):
        box = pane.div(margin_bottom='8px', font_size='12px')
        bar = box.div(display='flex', align_items='center', gap='8px',
                      margin_bottom='4px')
        bar.div(hint, color='#666', font_style='italic')
        bar.button('Copy', action='genro.textToClipboard(sample)',
                   sample=sample)
        box.div(sample, _class='selectable', white_space='pre',
                font_family='monospace', padding='4px 6px',
                border='1px dashed silver', border_radius='4px')

    def _shopping_struct(self, struct):
        r = struct.view().rows()
        r.cell('bought', name=' ', width='3em', dtype='B', edit=True)
        r.cell('item', name='Item', width='100%',
               edit=True, validate_notnull=True)
        r.cell('qty', name='Qty', width='5em', dtype='L', edit=True)
        r.cell('unit_price', name='Unit price', width='7em',
               dtype='N', edit=True, format='#,###.00')
        r.cell('line_total', name='Line total', width='8em',
               dtype='N', formula='qty*unit_price',
               totalize='.total_spent', format='#,###.00')
