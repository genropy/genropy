# -*- coding: utf-8 -*-

"Simple textBox"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    js_requires = "docu_components"

    def test_0_textbox_phone(self,pane):
        """Simple TextBox with validation (number of characters) and format"""
        fb=pane.formbuilder(cols=2)
        fb.textbox(lbl='Phone',value='^.phone_1',format='### ### #',validate_len='3:8',
                    validate_len_max='!!Too long',validate_len_min='!!Too short')
        fb.textbox(lbl='Phone 2',value='^.phone_2',format='(##)### ### #',displayFormattedValue=True)

    def test_1_regex(self, pane):
        "Validation regex mechanism: you can indicate which characters are available"
        fb = pane.formbuilder(cols=2,datapath='.data')
        fb.textBox(value='^.test',validate_regex=' ^[AB]*$', lbl='Type text', placeholder='Available characters:  ^[AB]*$')

    def test_2_diff(self, pane):
        "Use docu component to check for differences between a text and another"
        fb = pane.formbuilder()
        if not 'docu' in self.db.packages:
            return fb.div('Missing required docu package')
        fb.simpleTextArea('^.text_1', lbl='Text 1', height='50px', width='100%')
        fb.simpleTextArea('^.text_2', lbl='Text 2', height='50px', width='100%')
        fb.div('^.diff')                  
        pane.dataController("""var resultHtml=true;
                            var diff = diffUtil.calculateDifference(text_1, text_2, 'html');
                                console.log(diff);
                                SET .diff=diff;
                            """, 
                            text_1='=.text_1', text_2='^.text_2', _if='text_1')