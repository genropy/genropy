# -*- coding: utf-8 -*-

"Shortcuts"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase"

    def test_0_shortcut(self,pane):
        "Possibility to define custom shortcuts. Insert name and press Ctrl+Shift+H to trigger button action"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.name', lbl='Name')
        fb.button('Say hi', _shortcut='Ctrl+Shift+H').dataController('alert("Hi "+name)', name='=.name')

    def test_1_sound(self, pane):
        "Play sound when characters are digited in field"
        box = pane.div()
        box.textarea(value='^.text_msg', connect_onkeyup="""var tgt = $1.target
                                                        var my_text = tgt.value
                                                        var remaining = 10 - my_text.length
                                                        if(remaining<3){
                                                            genro.playSound('ping')
                                                        }
                                                        """)
    


