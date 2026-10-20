"""groupletGrid tab strip: a label template with a live total, ordered by a field.

  test_01_template_sorted — chapters as vtabs. `titleTemplate` shows the
                            code, the name and the chapter total (the
                            accounts' amounts summed, `sums=`), updated as
                            you type an amount. `sortField='code'` orders
                            the strip as codes are read (2 before 10):
                            change a code and the tab moves. The stored
                            Bag keeps its order (Show stored order, on the right).
  test_02_sort_store      — the same with `sortStore=True`: the stored Bag
                            is reordered too, in place (no row is removed
                            and inserted, nested grids keep their rows).
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    TITLE = dict(
        template='<span style="font-family:monospace;margin-right:.4em">$code</span>'
                 '$name<span style="margin-left:.6em;opacity:.7">$total</span>',
        formats=dict(total='#,##0.00'),
        sums=dict(total='accounts.amount'))

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def _chapters(self):
        chapters = Bag()
        for key, code, name, amounts in (('r_a', '10', 'Crew', (1200, 800)),
                                         ('r_b', '2', 'Cast', (5000,)),
                                         ('r_c', '1', 'Story and rights', (300, 150, 50))):
            accounts = Bag()
            for i, amount in enumerate(amounts):
                accounts.setItem('a_%s' % i, Bag(dict(code='%s.%s' % (code, i + 1),
                                                      name='Account %s' % (i + 1),
                                                      amount=amount)))
            chapters.setItem(key, Bag(dict(code=code, name=name, accounts=accounts)))
        return chapters

    def _grid(self, pane, nodeId, **kwargs):
        pane.data('.chapters', self._chapters())
        bc = pane.borderContainer(height='360px', border='1px solid silver')
        side = bc.contentPane(region='right', width='160px', padding='8px',
                              border_left='1px solid silver')
        side.button('Show stored order',
                    action="""var codes = rows.getNodes().map(function(n){
                                  return n.getValue().getItem('code');});
                              SET .order = codes.join('\\n');""",
                    rows='=.chapters')
        side.div('^.order', white_space='pre', font_family='monospace')
        bc.contentPane(region='center').groupletGrid(
            storepath='.chapters', handler=self.chapter_tab,
            nodeId=nodeId, layout='vtabs', fillParent=True,
            titleTemplate=self.TITLE, sortField='code',
            delitem=True, emptyTitle='!!New chapter',
            defaultRow=dict(code='', name=''), **kwargs)

    def test_01_template_sorted(self, pane):
        """Tab label: code, name and live total; tabs ordered by code"""
        self._grid(pane, 'tabsort_chapters')

    def test_02_sort_store(self, pane):
        """sortStore=True: the stored Bag follows the tab order"""
        self._grid(pane, 'tabsort_store', sortStore=True)

    @public_method
    def chapter_tab(self, pane, **kwargs):
        fb = pane.formlet(cols=2, padding='8px')
        fb.textbox(value='^.code', lbl='Code', width='6em')
        fb.textbox(value='^.name', lbl='Name')
        pane.groupletGrid(storepath='.accounts', handler=self.account_row,
                          delitem=True, defaultRow=dict(amount=0))

    @public_method
    def account_row(self, pane, **kwargs):
        fb = pane.formlet(cols=3)
        fb.textbox(value='^.code', lbl='Code', width='6em')
        fb.textbox(value='^.name', lbl='Name')
        fb.numberTextBox(value='^.amount', lbl='Amount', format='#,##0.00')
