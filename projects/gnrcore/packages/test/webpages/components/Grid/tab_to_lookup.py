# -*- coding: utf-8 -*-

"""Tab from an amount to a lookup in an editable bag grid."""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"

    def test_0_tab_to_lookup(self, pane):
        """Enter 10 in Debit on the first row and press Tab. Type 'Adjustment' in Reason.
        Repeat with 10 in Credit on the second row. Both times the lookup should
        stay focused and let you select the reason and tab to Description."""
        rows = Bag()
        for key in ('debit', 'credit'):
            rows.setItem(key, Bag(dict(debit=None, credit=None, lookup=None,
                                       lookup_caption=None, description=None)), _pkey=key)
        pane.data('.seed', rows)
        pane.dataController('SET .ledger.rows = seed.deepCopy();', seed='=.seed', _onStart=True)
        pane.div('Out of balance', hidden='^.ledger.balance?=!#v',
                 position='absolute', right='3em')
        pane.dataController('SET .ledger.balance = rows.sum("debit") - rows.sum("credit");',
                            rows='^.ledger.rows', _if='rows')
        pane.bagGrid(frameCode='ledger', datapath='.ledger', storepath='.rows',
                     struct=self.ledger_struct, grid_canSelect=False, grid_canSort=False,
                     height='200px', addrow=False, delrow=False, autoToolbar=False)

    def ledger_struct(self, struct):
        r = struct.view().rows()
        r.cell('side', hidden=True, calculated=True,
               formula='(debit > 0 && "D") || (credit > 0 && "C")')
        r.cell('debit', name='Debit', width='8em', dtype='N', edit=True,
               totalize='.total_debit', editDisabled='==this.getRelativeData("#ROW.side")=="C"')
        r.cell('credit', name='Credit', width='8em', dtype='N', edit=True,
               totalize='.total_credit', editDisabled='==this.getRelativeData("#ROW.side")=="D"')
        r.cell('lookup', name='Reason', width='12em', caption_field='lookup_caption',
               edit=dict(tag='dbselect', method='sample_reasons', selected_caption='.lookup_caption'))
        r.cell('lookup_caption', hidden=True)
        r.cell('description', name='Description', width='14em', edit=True)

    @public_method
    def sample_reasons(self, _id=None, _querystring='', **kwargs):
        options = Bag()
        query = (_querystring or '').strip('*').casefold()
        for code, caption in (('ADJ', 'Adjustment'), ('PAY', 'Payment')):
            if _id and _id != code:
                continue
            if not _id and query not in caption.casefold():
                continue
            options.setItem(code, None, _pkey=code, caption=caption)
        return options, dict(columns='caption', headers='Reason')
