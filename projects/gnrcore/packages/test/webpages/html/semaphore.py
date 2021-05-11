#!/usr/bin/python
# -*- coding: utf-8 -*-

"genro.dom.centerOn"

from builtins import object
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    
    def test_0_boolean(self, pane):
        "Show checkbox value as semaphore"
        pane.data('.bool_value', True)
        pane.lightbutton('^.bool_value',action="""SET .bool_value=event.shiftKey?null:!val;""",val='=.bool_value',
                            format='<div class="checkboxOn">&nbsp;</div>,<div class="checkboxOff">&nbsp;</div>,<div class="checkboxOnOff">&nbsp;</div>',
                            dtype='B', margin_bottom='10px')
        pane.div(value='^.bool_value', format='semaphore', dtype='B')
    
    def test_1_boolean(self,pane):
        "Same as before, but different semaphore syntax"
        pane.checkbox(value='^.bool_value',validate_notnull=True, margin_bottom='10px')
        pane.semaphore('^.bool_value')

    def test_2_boolean(self, pane):
        #DP A cosa serve tutta sta roba? E questo esempio cosa farebbe?
        pane.lightbutton('^.bool_value',action="""SET .bool_value=event.shiftKey?null:!val;""",val='=.bool_value',
                            format='<div class="checkboxOn">&nbsp;</div>,<div class="checkboxOff">&nbsp;</div>,<div class="checkboxOnOff">&nbsp;</div>',
                            dtype='B',  margin_bottom='10px')
        pane.div(format=dict(isbutton=True))

    def test_3_checkbox(self,pane):
        "Simple checkbox example"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.div(_class='').checkbox(value='^.pippo',validate_notnull=True)

        #DP Quindi?