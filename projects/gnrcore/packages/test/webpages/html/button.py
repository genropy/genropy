# -*- coding: utf-8 -*-

"Test Button"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def test_0_simplebutton(self,pane):
        "Simple button alert: insert text and launch alert"
        pane.textbox('^.message',lbl='Message')
        pane.button('Launch',action='alert(message)',
                        message='=.message')
    
    def test_1_buttonSet(self,pane):
        """Copy value into other field"""
        fb = pane.formbuilder()
        fb.textbox('^.sorgente',lbl='Sorgente')
        fb.button('Copia',action='SET .destinazione = v;',
                    v='=.sorgente')
        fb.textbox('^.destinazione',lbl='Destinazione')
    
    def test_2_buttonAsk(self,pane):
        "Button with ask: press button and insert fields into dialog"
        pane.button('Set value',
                    action="""SET .myvalue = myvalue;
                              SET .mycolor = mycolor;""",
                        ask=dict(title='Which one',
                                fields=[dict(name='myvalue',lbl='My value',
                                            validate_notnull=True),
                                        dict(name='mycolor',lbl='Color',
                                                tag='combobox',
                                                values='orange,green,blue')])
                                )
        pane.div('^.myvalue',color='^.mycolor')