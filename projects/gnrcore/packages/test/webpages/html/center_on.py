#!/usr/bin/python
# -*- coding: utf-8 -*-

"genro.dom.centerOn"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_parentContentPane(self, pane):
        "Push 'move' button to move FLOATING BLOCK. Position is relative to other block"
        pane.button('Move', action="genro.dom.centerOn('test1')", margin_bottom='10px')
        cp = pane.div(height="300px", width="300px", background_color="lime", position="relative")
        cp.div('FLOATING BLOCK', width="60px", height="60px", id="test1", background_color="white", 
                    border='solid 2px black', position="absolute", text_align='center', padding='20px')
        
    def test_1_parentWhere(self,pane):
        "Push 'move' button to move FLOATING BLOCK. Position is absolute."
        pane.button('Move', action="genro.dom.centerOn('test2a','test2b')", margin_bottom='10px')
        cp = pane.div(height="300px", width="300px", background_color="lime", id="test2b")
        cp.div('FLOATING BLOCK', width="60px", height="60px", id="test2a", background_color="white", 
                    border='solid 2px black', position="absolute", text_align='center', padding='20px')