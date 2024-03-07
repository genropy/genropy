# -*- coding: utf-8 -*-

"""Displayed value"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_dateTextBox(self, pane):
        "Same datetime value can be displayed in different ways"
        fb=pane.formbuilder(cols=3)
        fb.dataController('SET .date = new Date();', _onStart=True)
        fb.datetextbox(lbl='Full', value='^.date', readOnly=True)
        fb.div('^.date', dtype='DH', mask='Masked value:%s')
        fb.div('^.date')
        
    def test_1_numberTextBox(self, pane):
        "Same currency value can be displayed in different ways"
        fb=pane.formbuilder(cols=3)
        fb.data('.number',300)
        fb.numberTextBox(lbl='No constraints',value='^.number')
        fb.CurrencyTextBox(value='^.number', format_pattern='##0.00000', lbl='Currency')
        fb.div('^.number', format='##0.00000', mask='Masked value:%s')

    def test_2_pippo(self, pane):
        "Not just values, but you can display attributes as well"
        pane.data('.alfa', custom_attr='Hi there')
        pane.div(value='^.alfa?custom_attr')

    def test_3_numberTextBox_pattern(self, pane):
        "Display currency value in pattern or using currencyTextBox"
        fb=pane.formbuilder(cols=1)
        fb.data('.number',33)
        fb.numberTextBox(value='^.number',format='$ #,###.000',lbl='Format pattern')
        fb.div('^.number',lbl='Standard')
        fb.currencyTextBox(value='^.number',lbl='Currency')

    def test_4_textbox_regex(self,pane):
        "Validations: try using ![?]{2,2} characters"
        fb=pane.formbuilder(cols=2)
        fb.textbox(lbl='Address', value='^.address', validate_regex='}{!][?')

    def test_5_textbox_phone(self,pane):
        "Different ways to display phone numbers"
        fb=pane.formbuilder(cols=2)
        fb.textbox(lbl='Phone',value='^.phone_1',format='### ### #',validate_len='3:8',
                    validate_len_max='!!Too long',validate_len_min='!!Too short')
        fb.textbox(lbl='Phone 2',value='^.phone_2',format='(##)### ### #',displayFormattedValue=True)
        fb.textbox(lbl='Phone 3',value='^.phone_3',format='(##)## ## #')

    def test_6_filteringSelect(self, pane):
        "displayedValue in comboBox"
        fb=pane.formbuilder(cols=2)
        fb.filteringSelect(lbl='Filtering',value='^.filtering',values='pippo:Pippo,pluto:Pluto,paperino:Paperino')
        fb.div('^.filtering?_displayedValue')

    def test_7_numberTextBox_longdecimal(self, pane):
        "Display long decimal"
        fb=pane.formbuilder(cols=1)
        fb.numberTextBox(value='^.longdec',lbl='Long decimal',format='#,###.000000')
        fb.div('^.longdec')

    def test_9_numberTextBox_variable_places(self, pane):
        "Define format in field"
        fb=pane.formbuilder(cols=1)
        fb.textbox(value='^.format',lbl='Format',default='#,###.00')
        fb.numberTextBox(value='^.longdec',lbl='Long decimal',format='^.format')
        fb.div('^.longdec')
