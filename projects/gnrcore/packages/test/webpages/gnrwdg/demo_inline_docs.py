"""Inline docs, grouplet cards and grids: one walk-through of a customer.

Needs <experimental><gui inlinedoc="true"/></experimental> in the
instanceconfig and a logged user: sys/ep_doc never answers a guest. A user
with the tag _DOC_ (or doc_<package>) is a documenter: in documentation mode
the ⓘ of an empty doc shows red and a click writes the note in place, in the
inlinedoc storage.

  test_0_setup       build and link the demo manual once, turn documentation
                     mode on and off
  test_1_customer    the customer record form made of groupletCards: band,
                     fold, red band on a missing VAT, the card's ⓘ
  test_2_addresses   the same card_profile resource as a groupletGrid: blank
                     row, Cmd/Shift selection, copy and paste, drag, cards or
                     tabs; one doc for every row, a note filled with each row
  test_3_fields      fields of adm.user: one doc per column, the same in every
                     form, and the ⓘ of the manual's section
  test_4_view        a table handler view: the ⓘ of the table

The doc of a page and of its parts, and how the whole thing works, is
webpages/gnrwdg/test_page_doc.py.
"""
import os

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

try:
    from sphinx.cmd.build import build_main
except ImportError:
    build_main = None

ADDRESSES = (('Via Roma 1', 'Milano', 'MI'), ('Corso Francia 12', 'Torino', 'TO'),
             ('Via Sparano 3', 'Bari', 'BA'), ('Piazza Maggiore 6', 'Bologna', 'BO'))


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletCardHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler,
                     th/th:TableHandler"""

    def test_0_setup(self, pane):
        """Build and link the demo manual, documentation mode"""
        bar = pane.div(display='flex', gap='12px', align_items='center')
        bar.button('!!Build and link the demo manual', action='FIRE .build;')
        bar.checkbox(value='^gnr.docModeVisible', label='!!Documentation mode')
        pane.div('^.result', margin_top='6px')
        pane.dataRpc('.result', self.buildDemoManual, _fired='^.build', _lockScreen=True)

    @public_method
    def buildDemoManual(self):
        if build_main is None:
            return 'Sphinx is not installed: pip install sphinx myst-parser'
        source = os.path.join(self.site.gnrapp.packages['test'].packageFolder, 'docs', 'manual')
        build = self.site.storageNode('site:_demo_manual', autocreate=True)
        if build_main(['-q', '-b', 'html', source, build.internal_path]):
            return 'The demo manual did not build'
        url = 'site:_demo_manual/users.html'
        with self.db.table('adm.helpdoc').recordToUpdate(title='Demo manual', insertMissing=True) as rec:
            rec['title'] = 'Demo manual'
            rec['url'] = url
        self.db.commit()
        self.site.manual_cache.clear()
        return f'Built and linked to everybody as {url}. Reload the page.'

    def test_1_customer(self, pane):
        """The customer form, made of groupletCards"""
        street, city, province = ADDRESSES[0]
        pane.data('.customer', Bag(dict(name='ACME Spa', vat='',
                                        shipping=Bag(dict(street=street, city=city,
                                                          province=province)))))
        form = pane.frameForm(frameCode='demo_customer', height='360px', datapath='.customer_form',
                              border='1px solid silver')
        form.formStore(storeType='Item', handler='memory', locationpath='.#parent.customer')
        form.top.slotToolbar('*,semaphore,formcommands,5')
        box = form.center.contentPane(datapath='.record', padding='10px', overflow='auto')
        main = box.groupletCard(title='!!Customer', collapsible=True, margin_bottom='10px',
                                doc='grouplet:test:demo_customer')
        fb = main.formlet(cols=2)
        fb.textbox(value='^.name', lbl='Name', validate_notnull=True)
        fb.textbox(value='^.vat', lbl='VAT', validate_notnull=True)
        box.groupletCard(datapath='.shipping', resource='card_profile')
        form.dataController('this.form.load()', _onStart=True)

    def test_2_addresses(self, pane):
        """The same resource as a grid of shipping addresses"""
        rows = Bag()
        for i, (street, city, province) in enumerate(ADDRESSES):
            rows.setItem(f'r_{i}', Bag(dict(street=street, city=city, province=province)))
        pane.data('.addresses', rows)
        pane.data('.layout', 'cards')
        bar = pane.div(display='flex', gap='0.6em', align_items='center', margin_bottom='8px')
        bar.div('!!Layout', color='#666')
        bar.filteringSelect(value='^.layout', values='cards:!!Cards,tabs:!!Tabs', width='10em')
        pane.dataController("""const c = genro.nodeById(grid_id)?.gridController;
                               if (c && c.layout !== layout) { c.setLayout(layout); }""",
                            layout='^.layout', grid_id='demo_addresses')
        pane.groupletGrid(storepath='.addresses', resource='card_profile', nodeId='demo_addresses',
                          chromeSide='top', cols=4, min_width='16em', rowCheckbox=True,
                          copyitem=True, titleField='city', emptyTitle='!!New address',
                          selectionmenu=dict(copy=True, exportXls=True, print=True, delete=True),
                          defaultRow=dict(street='', city='', province=''))

    def test_3_fields(self, pane):
        """Fields of adm.user: one doc per column"""
        fb = pane.formlet(cols=2, table='adm.user', datapath='.user')
        fb.field('username')
        fb.field('email')
        fb.field('firstname')
        fb.field('lastname')

    def test_4_view(self, pane):
        """A table handler view: the ⓘ of the table"""
        pane.borderContainer(height='260px').contentPane(region='center').plainTableHandler(
            table='adm.user', viewResource='View')
