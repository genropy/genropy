#!/usr/bin/python
# -*- coding: utf-8 -*-

"genro.dom.centerOn"

from builtins import object
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    
    def test_0_boolean(self, pane):
        "Show checkbox value as semaphore, checkbox has null value"
        pane.lightbutton('^.bool_value',action="""SET .bool_value=event.shiftKey?null:!val;""",val='=.bool_value',
                            format='<div class="checkboxOn">&nbsp;</div>,<div class="checkboxOff">&nbsp;</div>,<div class="checkboxOnOff">&nbsp;</div>',
                            dtype='B', margin_bottom='10px')
        pane.div(value='^.bool_value', format='semaphore', dtype='B')
    
    def test_1_boolean(self,pane):
        "Same as before, but different semaphore syntax, normal checkbox without null value"
        pane.checkbox(value='^.bool_value',validate_notnull=True, margin_bottom='10px')
        pane.semaphore('^.bool_value')

    def test_3_checkbox(self,pane):
        "Same as before, but checkbox default value is True on loading, use of formbuilder"
        fb = pane.formbuilder(cols=2,border_spacing='3px', margin_right='10px')
        fb.data('.bool_value', True)
        fb.div(_class='').checkbox(value='^.bool_value',validate_notnull=True)
        fb.semaphore('^.bool_value')