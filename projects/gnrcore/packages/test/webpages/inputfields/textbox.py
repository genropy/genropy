# -*- coding: utf-8 -*-

"Simple textBox"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_textbox_phone(self,pane):
        """Simple TextBox with validation (number of characters) and format"""
        fb=pane.formbuilder(cols=2)
        fb.textbox(lbl='Phone',value='^.phone_1',format='### ### #',validate_len='3:8',
                    validate_len_max='!!Too long',validate_len_min='!!Too short')
        fb.textbox(lbl='Phone 2',value='^.phone_2',format='(##)### ### #',displayFormattedValue=True)