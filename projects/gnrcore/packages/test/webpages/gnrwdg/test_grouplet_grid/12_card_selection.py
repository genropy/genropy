"""groupletGrid selection on cards and across grids.

  test_01_cards_checkbox — `rowCheckbox=True` on a card grid: tick a card,
                           Shift+tick for a range, the box in the bar for
                           all. The bar below counts them, deletes them
                           together, and its kebab runs `selectionmenu`
                           actions (Mark as VIP) with `rowKeys`. Esc clears.
  test_02_selection_group — three items, each with its own details grid
                           (entry row and one-line rows, as a budget item).
                           The details grids share `selectionGroup`: tick
                           rows in several items and any bar counts them
                           all; Approve marks them approved and the delete
                           asks once for all of them. The actions get
                           `selection` = [{grid, rowKeys}], one per grid.
                           The item cards share their own group too.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    MARK_VIP = ("rowKeys.forEach(function(k){"
                "grid.dataStore.updateRow(k, {vip: true});});")
    APPROVE = ("selection.forEach(function(s){s.rowKeys.forEach(function(k){"
               "s.grid.dataStore.updateRow(k, {status: 'approved'});});});"
               "grid.clearSelection(true);")
    DETAIL_TEMPLATE = ('<div style="display:flex;gap:1em">'
                       '<span style="flex:1">$description</span>'
                       '<span>$amount</span>'
                       '<span style="width:7em">${&#10003; $status}</span></div>')

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_cards_checkbox(self, pane):
        """Tick cards to act on several of them"""
        contacts = Bag()
        for i, name in enumerate(('Alice', 'Bruno', 'Carla', 'Dario', 'Elena')):
            contacts.setItem('r_%s' % i, Bag(dict(name=name, role='Crew', vip=False)))
        pane.data('.contacts', contacts)
        pane.groupletGrid(storepath='.contacts', handler=self.contact_card,
                          nodeId='sel_contacts', cols=3, min_width='14em',
                          delitem=True, rowCheckbox=True,
                          selectionmenu=dict(delete=True,
                                             vip=dict(label='Mark as VIP',
                                                      action=self.MARK_VIP)),
                          defaultRow=dict(name='', role='', vip=False))

    def test_02_selection_group(self, pane):
        """Rows ticked in several grids form one selection"""
        items = Bag()
        for i, (name, details) in enumerate((('Camera', (('Body', 900), ('Lenses', 450))),
                                             ('Lights', (('Kit', 300),)),
                                             ('Sound', (('Mic', 120), ('Boom', 80))))):
            rows = Bag()
            for j, (description, amount) in enumerate(details):
                rows.setItem('d_%s' % j, Bag(dict(description=description,
                                                 amount=amount)))
            items.setItem('i_%s' % i, Bag(dict(name=name, details=rows)))
        pane.data('.items', items)
        pane.groupletGrid(storepath='.items', handler=self.item_card,
                          nodeId='sel_items', delitem=True, rowCheckbox=True,
                          selectionGroup='sel_demo_items',
                          defaultRow=dict(name=''))

    @public_method
    def contact_card(self, pane, **kwargs):
        fb = pane.formlet(cols=1)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.role', lbl='Role')
        fb.checkbox(value='^.vip', label='VIP')

    @public_method
    def item_card(self, pane, **kwargs):
        pane.formlet(cols=1).textbox(value='^.name', lbl='Item')
        pane.groupletGrid(storepath='.details', handler=self.detail_entry,
                          additem='entry', delitem=True, rowCheckbox=True,
                          rowTemplate=self.DETAIL_TEMPLATE,
                          selectionGroup='sel_demo_details',
                          selectionmenu=dict(delete=True,
                                             approve=dict(label='Approve',
                                                          action=self.APPROVE)),
                          defaultRow=dict(amount=0))

    @public_method
    def detail_entry(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.description', lbl='Description',
                   validate_notnull=True)
        fb.numberTextBox(value='^.amount', lbl='Amount', format='#,##0.00')
