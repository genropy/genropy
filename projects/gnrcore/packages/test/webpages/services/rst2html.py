# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_rst2html(self, pane):
        "Rst2HTML renders RST text into HTML"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.simpleTextArea(value='^.rst_text', lbl='Your RST text', height='300px', width='600px')
        fb.button('Render text').dataRpc('.rendered_text', self.render2Html, rst_text='=.rst_text')
        fb.simpleTextArea('^.rendered_text', lbl='HTML', height='300px', width='600px', editor=True, readOnly=True)

    @public_method
    def render2Html(self, rst_text=None):
        rst_service = self.site.getService('rst2html')
        rendered_text = rst_service(rst_text)
        return rendered_text