"""groupletGrid entry row (`additem='entry'`) inside a record form.

  test_01_entry_form — a memory form with chapters as tabs, each with a
                       details grid with an entry row. Type a detail and,
                       without pressing Enter:
                         · the semaphore turns to changed (a pending entry
                           is a change of the form);
                         · Save adds the row first, then saves;
                         · another chapter tab, or Cards / Tabs, adds it
                           first too.
                       A blank Description or a negative Amount stops all
                       of these with the field's message. More… opens a
                       popup of entry fields: Enter there adds the row,
                       Esc goes back to the entry row; a dragged detail can
                       be dropped on it as on the entry row.
                       The side panel lists the rows stored in the record.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    DETAIL_TEMPLATE = ('<div style="display:flex;gap:1em"><span style="flex:1">$description'
                       '${ · <i>$note</i>}</span><span>$amount</span></div>')
    POPUP_WIRING = ("this.attributeOwnerNode('_gg_root').gridController"
                    ".attachEntryPopup(this.getParentNode().getDomNode());")

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_entry_form(self, pane):
        """Pending entries are committed by save, tab and layout switches"""
        chapters = Bag()
        for key, name, details in (('c_1', 'Crew', (('Director', 5000),)),
                                   ('c_2', 'Equipment', (('Camera', 900), ('Lights', 300)))):
            rows = Bag()
            for i, (description, amount) in enumerate(details):
                rows.setItem('d_%s' % i, Bag(dict(description=description, amount=amount)))
            chapters.setItem(key, Bag(dict(name=name, details=rows)))
        pane.data('.budget', Bag(dict(chapters=chapters)))
        form = pane.frameForm(frameCode='entry_form', height='460px',
                              datapath='.entry_form', border='1px solid silver')
        form.formStore(storeType='Item', handler='memory',
                       locationpath='.#parent.budget')
        bar = form.top.slotToolbar('5,layout,*,semaphore,formcommands,5')
        bar.layout.multiButton(value='^#FORM.layout', values='tabs:Tabs,cards:Cards')
        bc = form.center.borderContainer(datapath='.record')
        side = bc.contentPane(region='right', width='180px', padding='8px',
                              border_left='1px solid silver')
        side.div('Stored details', font_weight='600')
        side.div('^#FORM.dump', white_space='pre', font_family='monospace', font_size='12px')
        bc.dataFormula('#FORM.dump',
                       """chapters ? chapters.getNodes().map(function(c){
                              var d = c.getValue().getItem('details');
                              return c.getValue().getItem('name') + ': '
                                  + (d ? d.getNodes().map(function(n){
                                         return n.getValue().getItem('description');}).join(', ') : '');
                          }).join('\\n') : ''""",
                       chapters='^.chapters')
        bc.contentPane(region='center').groupletGrid(
            storepath='.chapters', handler=self.chapter_tab, nodeId='entry_form_chapters',
            layout='tabs', titleField='name', fillParent=True,
            defaultRow=dict(name=''))
        bc.dataController("""var grid = genro.nodeById('entry_form_chapters').gridController;
                             if (grid && layout && grid.layout !== layout) grid.setLayout(layout);""",
                          layout='^#FORM.layout')
        bc.dataController('this.form.load()', _onStart=True)

    @public_method
    def chapter_tab(self, pane, **kwargs):
        pane.formlet(cols=1, padding='6px').textbox(value='^.name', lbl='Chapter')
        pane.groupletGrid(storepath='.details', handler=self.detail_entry,
                          additem='entry', delitem=True,
                          rowTemplate=self.DETAIL_TEMPLATE,
                          defaultRow=dict(amount=0))

    @public_method
    def detail_entry(self, pane, **kwargs):
        fb = pane.formlet(cols=3)
        fb.textbox(value='^.description', lbl='Description', validate_notnull=True)
        fb.numberTextBox(value='^.amount', lbl='Amount', format='#,##0.00',
                         validate_min=0, validate_min_error='!!Amount cannot be negative')
        more = fb.lightButton('More…', lbl='&nbsp;', _class='gg-demo-more')
        popup = more.tooltipPane(evt='onclick')
        box = popup.formlet(cols=1, padding='8px')
        box.dataController(self.POPUP_WIRING, _onBuilt=1)
        box.textbox(value='^.note', lbl='Note')
