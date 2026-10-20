"""groupletGrid collapsible cards: a card folds to one summary line.

  test_01_closed_with_total — `collapsible='closed'`: the accounts start
                              folded, each on one line from
                              `collapsedTemplate` (code, name and the total
                              of its details, live). The chevron or a click
                              on the line opens a card; Reload rows replaces
                              the rows Bag with a copy: the cards keep their
                              open or folded state.
  test_02_open_all          — `collapsible=True`: the cards start open;
                              Collapse all / Expand all call collapseAll().
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    SUMMARY = dict(
        template='<b style="font-family:monospace">$code</b> $name'
                 '<span style="float:right">$total</span>',
        formats=dict(total='#,##0.00'),
        sums=dict(total='details.amount'))

    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def _accounts(self):
        accounts = Bag()
        for i, (code, name, amounts) in enumerate((('01', 'Director', (5000, 1200)),
                                                   ('02', 'Camera crew', (2400, 800, 300)),
                                                   ('03', 'Catering', (650,)))):
            details = Bag()
            for j, amount in enumerate(amounts):
                details.setItem('d_%s' % j, Bag(dict(description='Line %s' % (j + 1),
                                                     amount=amount)))
            accounts.setItem('a_%s' % i, Bag(dict(code=code, name=name, details=details)))
        return accounts

    def test_01_closed_with_total(self, pane):
        """Folded accounts show code, name and total"""
        pane.data('.accounts', self._accounts())
        pane.button('Reload rows',
                    action="SET .accounts = rows.deepCopy();", rows='=.accounts')
        pane.groupletGrid(storepath='.accounts', handler=self.account_card,
                          nodeId='coll_closed', collapsible='closed',
                          collapsedTemplate=self.SUMMARY, delitem=True,
                          titleField='name', emptyTitle='!!New account',
                          defaultRow=dict(code='', name=''))

    def test_02_open_all(self, pane):
        """Open cards, folded and opened all together"""
        pane.data('.accounts', self._accounts())
        bar = pane.div(display='flex', gap='6px', margin_bottom='6px')
        bar.button('Collapse all',
                   action="genro.nodeById('coll_open').gridController.collapseAll(true);")
        bar.button('Expand all',
                   action="genro.nodeById('coll_open').gridController.collapseAll(false);")
        pane.groupletGrid(storepath='.accounts', handler=self.account_card,
                          nodeId='coll_open', collapsible=True, cols=2,
                          min_width='22em', collapsedTemplate=self.SUMMARY,
                          defaultRow=dict(code='', name=''))

    @public_method
    def account_card(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.code', lbl='Code', width='5em')
        fb.textbox(value='^.name', lbl='Name')
        pane.groupletGrid(storepath='.details', handler=self.detail_row,
                          delitem=True, defaultRow=dict(amount=0))

    @public_method
    def detail_row(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.description', lbl='Description')
        fb.numberTextBox(value='^.amount', lbl='Amount', format='#,##0.00')
