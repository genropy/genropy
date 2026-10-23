"""groupletGrid `defaultRow` with values read from the data when a row is added.

  test_01_default_from_data — `defaultRow=dict(producer='=#FORM.record.main_producer')`:
                              pick the main producer above, then add a card
                              (+) or type in the entry row: the new row takes
                              the producer chosen at that moment. Change the
                              main producer and add again; a blank entry row
                              shows the new producer when it gets the focus.
  test_02_next_code         — `defaultRow=dict(code='==...')` worked out over the
                              rows when one is added: + proposes the next code
                              (04003 -> 04004), and `additem_focus='name'` puts
                              the caret on the name, not on the code badge
                              before it. In cards and in lazy vtabs.
"""
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    PRODUCERS = 'P01:Alpha Film,P02:Beta Studio,P03:Gamma Pictures'

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_default_from_data(self, pane):
        """New rows default to the producer chosen when they are added"""
        items = Bag()
        items.setItem('r_001', Bag(dict(name='Camera crew', producer='P01')))
        pane.data('.budget', Bag(dict(main_producer='P02', items=items,
                                      lines=Bag())))
        form = pane.frameForm(frameCode='default_row_form', height='520px',
                              datapath='.default_row_form',
                              border='1px solid silver')
        form.formStore(storeType='Item', handler='memory',
                       locationpath='.#parent.budget')
        form.top.slotToolbar('5,*,semaphore,formcommands,5')
        box = form.center.contentPane(datapath='.record', padding='10px',
                                      overflow='auto')
        fb = box.formlet(cols=1, width='20em')
        fb.filteringSelect(value='^.main_producer', lbl='Main producer',
                           values=self.PRODUCERS)
        box.div('Items (cards, + adds)', font_weight='600', margin='12px 0 4px')
        box.groupletGrid(storepath='.items', handler=self.item_card,
                         nodeId='dflt_items',
                         cols=2, min_width='22em', delitem=True,
                         defaultRow=dict(name='', producer='=#FORM.record.main_producer'))
        box.div('Details (entry row)', font_weight='600', margin='12px 0 4px')
        box.groupletGrid(storepath='.lines', handler=self.item_card,
                         nodeId='dflt_lines',
                         additem='entry', delitem=True,
                         defaultRow=dict(producer='=#FORM.record.main_producer'))
        box.dataController('this.form.load()', _onStart=True)

    NEXT_CODE = ("==String(Math.max(4000, ...rows.getNodes().map("
                 "(n) => parseInt(n.getValue().getItem('code'), 10) || 0)) + 1).padStart(5, '0')")

    def test_02_next_code(self, pane):
        """+ proposes the next code and puts the caret on the name"""
        for store in ('.accounts', '.tab_accounts'):
            accounts = Bag()
            for i, name in enumerate(('Crew', 'Cast', 'Equipment'), start=1):
                accounts.setItem('r_%s' % i, Bag(dict(code='0400%s' % i, name=name)))
            pane.data(store, accounts)
        pane.div('Cards', font_weight='600', margin='0 0 4px')
        pane.groupletGrid(storepath='.accounts', handler=self.account_card,
                          nodeId='dflt_next_cards', cols=3, min_width='14em',
                          delitem=True, additem_focus='name',
                          defaultRow=dict(code=self.NEXT_CODE, name=''))
        pane.div('Lazy vtabs', font_weight='600', margin='12px 0 4px')
        pane.div(height='220px', border='1px solid silver').groupletGrid(
            storepath='.tab_accounts', handler=self.account_card,
            nodeId='dflt_next_tabs', layout='vtabs', lazyTabs=True,
            titleField='name', emptyTitle='!!New account', fillParent=True,
            delitem=True, additem_focus='name',
            defaultRow=dict(code=self.NEXT_CODE, name=''))

    @public_method
    def account_card(self, pane, **kwargs):
        row = pane.div(display='flex', gap='6px', align_items='center', padding='4px')
        row.textbox(value='^.code', width='5em', placeholder='Code')
        row.textbox(value='^.name', width='100%', placeholder='Name')

    @public_method
    def item_card(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.name', lbl='Name')
        fb.filteringSelect(value='^.producer', lbl='Producer',
                           values=self.PRODUCERS)
