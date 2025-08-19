# -*- coding: utf-8 -*-


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase,msgarea_component:MsgArea"
    
    def test_0_textarea(self, pane):
        "Test textArea with connect_onkeyup to show available characters"
        box = pane.div()
        box.textarea(value='^.text_msg', connect_onkeyup="""var tgt = $1.target
                                                        var my_text = tgt.value
                                                        var remaining = 30 - my_text.length
                                                        SET .rem = remaining
                                                        SET .clr = (remaining<10)?'red':'grey'
                                                        if(remaining<3){
                                                            genro.playSound('ping')
                                                        }
                                                        if(remaining<0){
                                                            tgt.value = my_text.slice(0,30)
                                                        }
                                                        """)
        last_line = box.div(font_style='italic', font_size='8pt')
        last_line.span('Remaining: ')
        last_line.span('^.rem', color='^.clr')

    def test_1_textarea(self, pane):
        "Same result but using messageArea custom component"
        fb = pane.formbuilder()
        self.messageArea(fb, value='^.my_message', max_len=30, height='50px', width='200px')
    
    def test_2_textarea(self, pane):
        "Same result but using messageArea custom component, with more parameters"
        fb = pane.formbuilder()
        self.messageArea(fb, value='^.my_message', max_len=10, color_ok='lime', color_warning='purple',
                                auto_skip=True, height='50px', width='200px')

    def test_3_textarea(self, pane):
        "Same result but using messageArea custom component, with more parameters specified in the form"
        fb = pane.formbuilder()
        fb.numberTextBox(value='^.max_len', lbl='Max length')
        fb.textBox(value='^.color_ok', lbl='Color if ok')
        fb.messageArea(value='^.my_message', max_len='=.max_len', color_ok='=.color_ok', color_warning='purple',
                                auto_skip=True, height='50px', width='200px', lbl='Message')