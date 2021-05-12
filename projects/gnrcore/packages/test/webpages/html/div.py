# -*- coding: utf-8 -*-

"Test HTML DIV"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 

    def test_0_helloworld(self,pane):
        "Hello world flat text"
        pane.data('.mytext','Hello world')
        pane.div('^.mytext',font_size='15px')

    def test_1_helloworld_dynamic(self,pane):
        "Hello world dynamic, with inserted text"
        pane.textbox(value='^.mytext')
        pane.div('^.mytext',font_size='15px')

    def test_2_helloworld_dynamic(self,pane):
        "Hello world font-size dynamic, with text and parameters inserted"
        fb = pane.formbuilder()
        fb.textbox(value='^.mytext',lbl='Content')
        fb.textbox(value='^.font_size',lbl='Font size')
        fb.div('^.mytext',font_size='^.font_size')