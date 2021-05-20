# -*- coding: utf-8 -*-

"NumberTextBox"

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
