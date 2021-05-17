# -*- coding: utf-8 -*-

"Test HTML DIV"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
                
    def test_0_helloworld(self,pane):
        "Hello world flat div with no attributes"
        pane.div('Hello World',font_size='15px')

    def test_1_helloworld(self,pane):
        "Hello world flat div with attributes, text pre-loaded in path with 'data'"
        pane.data('.mytext','Hello world')
        pane.div('^.mytext',font_size='15px', height='50px', width='100px', 
                        border='2px dotted red', background_color='yellow')

    def test_2_some_span(self, pane):
        "Some spans"
        pane.span('this is: ')
        pane.span('green ', color='green')
        pane.span('yellow ', color='blue')
        pane.span('red', color='red')

    def test_3_helloworld_dynamic(self,pane):
        "Hello world dynamic, with inserted text"
        pane.textbox(value='^.mytext')
        pane.div('^.mytext',font_size='15px')

    def test_4_helloworld_dynamic(self,pane):
        "Hello world font-size dynamic, with text and parameters inserted"
        fb = pane.formbuilder()
        fb.textbox(value='^.mytext',lbl='Content')
        fb.textbox(value='^.font_size',lbl='Font size')
        fb.div('^.mytext',font_size='^.font_size')