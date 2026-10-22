"""One doc address, one popup: sys/ep_doc and genro.dlg.docPopup.

sys/ep_doc answers only a logged user (never a guest): log in to the
instance first, or the docs read at an address say none is available.

  test_1_card    the ⓘ of a card whose resource declares its doc: the page
                 holds only the address grouplet:test:card_profile, the doc is
                 read from sys/ep_doc as it first opens and filled on the
                 card's data; the inline doc next to it is never fetched
  test_2_grid    a Bag-backed grid of the same resource: each row's doc is
                 filled with that row's values in the browser, nothing is
                 posted; edit a city and open its doc again
  test_3_helper  a field with helpcode: the help opens in the same popup;
                 with the developer tools visible the ⓘ edits it as before
  test_4_address any address opened by code, and the doc as a page of its
                 own (the link is valid while this page is open)
"""
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletCardHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_1_card(self, pane):
        """A resource doc read at its address, an inline doc kept in the page"""
        pane.data('.shipping', Bag(dict(street='Via Roma 1', city='Milano', province='MI')))
        row = pane.div(display='flex', gap='12px', align_items='start')
        row.groupletCard(datapath='.shipping', resource='card_profile', width='22em')
        row.groupletCard(datapath='.shipping', resource='card_profile', width='22em',
                         title='!!Inline doc', doc='<p>Goods for <b>$city</b> leave every morning.</p>')

    def test_2_grid(self, pane):
        """Each row's doc on its own values, filled in the browser"""
        rows = Bag()
        for i, (city, province) in enumerate((('Milano', 'MI'), ('Torino', 'TO'), ('Bari', 'BA'))):
            rows.setItem('r_%s' % i, Bag(dict(street='Via Roma %s' % (i + 1), city=city,
                                              province=province)))
        pane.data('.rows', rows)
        pane.groupletGrid(storepath='.rows', resource='card_profile', chromeSide='top',
                          cols=3, min_width='16em', nodeId='doc_rows')

    def test_3_helper(self, pane):
        """A field help in the same popup"""
        pane.data('gnr.helpers.%s.delivery' % self.pagename, None,
                  en='Leave the parcel at the door.\n\nRing twice: the bell is weak.',
                  it='Lasciare il pacco alla porta.\n\nSuonare due volte: il campanello è debole.')
        fb = pane.formlet(cols=2, datapath='.order')
        fb.textbox(value='^.delivery', lbl='!!Delivery notes', helpcode='delivery')
        fb.textbox(value='^.reference', lbl='!!Reference')

    def test_4_address(self, pane):
        """An address opened by code, and as a page of its own"""
        bar = pane.div(display='flex', gap='12px', align_items='center')
        bar.button('!!Open the doc', action="""genro.dlg.openDoc(this.domNode, address,
                                                    {fill: tpl => tpl.replace(/\\$\\w+/g, '…')});""",
                   address='grouplet:test:card_profile')
        bar.button('!!Open it as a page', action='genro.openBrowserTab(genro.dlg.docUrl(address));',
                   address='grouplet:test:card_profile')
        bar.button('!!Missing doc', action='genro.dlg.openDoc(this.domNode, address);',
                   address='grouplet:test:no_such_resource')
