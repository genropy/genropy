# -*- coding: utf-8 -*-

"NumberTextBox"
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
        
    def test_0_numberTextBox(self, pane):
        "NumberTextBox and currencyTextBox, with and without constraints and use of Mask"
        fb=pane.formbuilder(cols=1)
        fb.numberTextBox(lbl='No constraints',value='^.number_1')
        fb.CurrencyTextBox(value='^.number_1',format_pattern='##0.00000',lbl='Currency')
        fb.div('^.number_1',format='##0.00000', mask='Masked value:%s')

    def test_1_numberTextBox_pattern(self, pane):
        "NumberTextBox with formattedValue. Check changes in console"
        fb=pane.formbuilder(cols=1)
        fb.data('.number',33)
        fb.numberTextBox(value='^.number',format='$ #,###.000',lbl='Format pattern')
        fb.dataController("console.log('changed',value);",value='^number')
        fb.div('^.number?_formattedValue',lbl='Formatted Value')
        fb.div('^.number',lbl='Original number')

    def test_2_numberTextBox_longdecimal(self, pane):
        "Long decimal using format, show real number without constraints in div"
        fb=pane.formbuilder(cols=1)
        fb.numberTextBox(value='^.longdec',lbl='Long decimal',format='#,###.000000')
        fb.div('^.longdec')

    def test_3_dataRpc(self, pane):
        "You can fill fields even in readOnly and manage attributes in different ways"
        fb = pane.formbuilder(cols=2,datapath='.data')
        fb.button('TEST',fire='.colors', colspan=2)
        fb.numberTextBox(value='^.number.color', readOnly=True)
        fb.numberTextBox(value='^.number.inattr?val', readOnly=True)
        
        fb.dataRpc('.number',self.testblu,_fired='^.colors')

    @public_method
    def testblu(self):
        a = Bag()
        a.setItem('color',3,wdg_color='green')
        a.setItem('inattr',None,val=44,wdg_val_color='red')
        return a

    def test_4_autoselect(self, pane):
        "With autoselect you can automatically select field content"
        fb = pane.formbuilder(cols=2,datapath='.data')
        fb.numberTextBox('^.number',lbl='Number',format='#.00', _autoselect=True)