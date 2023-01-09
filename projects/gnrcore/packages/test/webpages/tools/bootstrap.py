# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,bootstrap_components:BootstrapComponents"""

    def test_0_button(self, pane):
        """Bootstrap button class"""
        pane.lightbutton("This is a BS btn", _class='btn btn-primary').dataController("alert('Hi')")
        pane.div(margin='5px')
        pane.lightbutton("This is a BS outline btn", _class='btn btn-outline-secondary').dataController("alert('Hi')")
        pane.div(margin='5px')
        pane.lightbutton("This is a BS small disabled btn", 
                            _class='btn btn-secondary btn-sm', disabled=True).dataController("alert('Hi')")

    def test_1_card(self, pane):
        fb = pane.formbuilder(cols=1)
        fb.textbox('^.image_url', lbl='Image url')
        fb.textbox('^.title', lbl='Title')
        fb.textbox('^.text', lbl='Text')
        fb.textbox('^.destination_url', lbl='Destination url')
        pane.bsCard(title='^.title', image='^.image_url', text='^.text', btn_link='^.destination_url')