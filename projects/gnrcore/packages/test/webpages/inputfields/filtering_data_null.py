# -*- coding: utf-8 -*-

"""A required filteringSelect emptied from data (#1540)

  test_01_outside_form — a filteringSelect with validate_notnull outside any
                         form. Pick a VAT rate, then "Clear from data": the
                         select empties and stays quiet (no red, no
                         "Required field"). Click in it and leave: still
                         quiet. Pick a rate and clear it by hand, then
                         leave: that is a user change, so it is validated.
  test_02_entry_row    — invoice rows with an entry row: the VAT cell is a
                         values= select with validate_notnull. Fill a row
                         and press Enter: the row is added, the entry row is
                         cleared and no "Required field" is published. The
                         blank VAT cell is red while the entry row has the
                         focus, a field required to add the next row (#1544),
                         and quiet once the focus leaves the row.
"""

from gnr.core.gnrbag import Bag

VAT_VALUES = '22:22%,10:10%,4:4%,0:Exempt'


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_01_outside_form(self, pane):
        """Clear from data: no echo; clear by hand: validated"""
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.data('.vat', '22')
        fb.filteringSelect(value='^.vat', values=VAT_VALUES, lbl='VAT',
                           validate_notnull=True)
        fb.button('Clear from data', action='SET .vat=null;')
        fb.div('^.vat?=#v===null?"null":(#v===undefined?"undefined":#v)',
               lbl='Value')

    def test_02_entry_row(self, pane):
        """Add a row: no 'Required field' is published for the cleared VAT cell"""
        rows = Bag()
        rows.setItem('r_001', Bag(dict(description='Consulting',
                                       amount=100, vat='22')))
        pane.data('.rows', rows)
        bc = pane.borderContainer(height='320px', border='1px solid silver')
        center = bc.contentPane(region='center', padding='10px')
        center.groupletGrid(storepath='.rows',
                            struct=self._rows_struct,
                            nodeId='grpgrid_vat_entry',
                            fillParent=True,
                            additem='entry',
                            additem_label='!!New row',
                            delitem=True)

    def _rows_struct(self, struct):
        r = struct.view().rows()
        r.cell('description', name='Description', width='100%', edit=True)
        r.cell('amount', name='Amount', width='7em', dtype='N', edit=True,
               format='#,###.00')
        r.cell('vat', name='VAT', width='7em', edit=True, values=VAT_VALUES,
               validate_notnull=True)
