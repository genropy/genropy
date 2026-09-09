# -*- coding: utf-8 -*-

"Numeric keypad and calculator popup on numeric fields"

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_optIn(self, pane):
        """Both options off (no icon, same DOM as before), keypad only, keypad with calculator"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.plain', lbl='Off (regression)')
        fb.div('^.plain')
        fb.numberTextBox(value='^.pad', lbl='keypad=True', keypad=True)
        fb.div('^.pad')
        fb.numberTextBox(value='^.calc', lbl='keypad_calculator=True', keypad_calculator=True)
        fb.div('^.calc')

    def test_0b_size(self, pane):
        """The pad scales with the font of its own field; keypad_size='large' is the
        opt-out, an absolute touch target even on a small field"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.normal', lbl='Default font', keypad_calculator=True)
        fb.div('^.normal')
        fb.numberTextBox(value='^.small', lbl='Small font (11px)', keypad_calculator=True,
                         font_size='11px', width='7em')
        fb.div('^.small')
        fb.numberTextBox(value='^.wide', lbl='Big font (22px)', keypad_calculator=True,
                         font_size='22px')
        fb.div('^.wide')
        fb.numberTextBox(value='^.big', lbl="small font + keypad_size='large'",
                         keypad_calculator=True, keypad_size='large',
                         font_size='11px', width='7em')
        fb.div('^.big')
        fb.numberTextBox(value='^.big_pad', lbl="large, keypad only", keypad=True,
                         keypad_size='large')
        fb.div('^.big_pad')

    def test_1_format(self, pane):
        """Keypad on fields with format and places: the field keeps its own formatting"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.thousands', lbl='#,###.00', format='#,###.00', keypad=True)
        fb.div('^.thousands')
        fb.numberTextBox(value='^.longdec', lbl='#,###.000000', format='#,###.000000',
                         keypad_calculator=True)
        fb.div('^.longdec')
        fb.numberTextBox(value='^.integer', lbl='places=0', places='0', keypad=True)
        fb.div('^.integer')

    def test_2_currency(self, pane):
        """currencyTextBox inherits the option; numberSpinner is excluded (its arrows own the right edge)"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.currencyTextBox(value='^.amount', lbl='Currency', format_pattern='##0.00',
                           keypad_calculator=True)
        fb.div('^.amount')
        fb.numberSpinner(value='^.spin', lbl='numberSpinner (no icon)', keypad=True)
        fb.div('^.spin')

    def test_3_decimalSeparator(self, pane):
        """Decimal separator: the pad reads it from the field constraints, as the field does.
        Only the page locale has its dojo.cldr number bundle loaded, so a per-field
        locale= is not exercised here: it throws on any value, keypad or not."""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.dec', lbl='Decimal', format='#,##0.00', keypad=True)
        fb.div('^.dec')
        fb.numberTextBox(value='^.dec_calc', lbl='Decimal with calculator',
                         format='#,##0.000', keypad_calculator=True)
        fb.div('^.dec_calc')

    def test_4_notEditable(self, pane):
        """readOnly and disabled: the opener is hidden and takes no click"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.data('.ro', 1234.5)
        fb.data('.dis', 6789.25)
        fb.numberTextBox(value='^.ro', lbl='readOnly', readOnly=True, keypad=True)
        fb.numberTextBox(value='^.dis', lbl='disabled', disabled=True, keypad_calculator=True)
        fb.numberTextBox(value='^.togglable', lbl='disabled from data',
                         disabled='^.lock', keypad=True)
        fb.checkbox(value='^.lock', label='Lock the field above')

    def test_5_gridCellEdit(self, pane):
        """Keypad as a grid cell editor"""
        pane.data('.store', self._sampleRows())
        pane.bagGrid(frameCode='keypadgrid', title='Keypad in grid cells',
                     struct=self._gridStruct, storepath='.store',
                     height='300px', addrow=True, delrow=True)

    def _gridStruct(self, struct):
        r = struct.view().rows()
        r.cell('label', width='12em', name='Label', edit=True)
        r.cell('qty', width='8em', name='Qty', dtype='N',
               edit=dict(tag='numberTextBox', keypad=True))
        r.cell('price', width='10em', name='Price', dtype='N', format='#,###.00',
               edit=dict(tag='numberTextBox', keypad_calculator=True))

    def _sampleRows(self):
        data = Bag()
        data.setItem('r_0', Bag(dict(label='First', qty=3, price=12.5)))
        data.setItem('r_1', Bag(dict(label='Second', qty=10, price=99.9)))
        return data
