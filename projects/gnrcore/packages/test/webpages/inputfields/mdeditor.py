# -*- coding: utf-8 -*-

"MDEditor"
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
        
    def test_0_base(self, pane):
        pane.MDEditor(value='^.mycontent',height='300px',width='400px',htmlpath='.mycontent_html')


    def test_2_viewer(self, pane):
        pane.data('.mycontent','My *content*')
        pane.MDEditor(value='^.mycontent',height='300px',width='400px',viewer=True)



    def test_1_parametric(self, pane):
        bc = pane.borderContainer(height='800px',width='600px',border='1px solid silver')
        fb = bc.contentPane(region='top').formbuilder()
        fb.textbox('^.initialEditType',lbl='initialEditType')
        fb.textbox('^.initialValue',lbl='initialValue')
        fb.textbox('^.previewStyle',lbl='previewStyle')
        bc.contentPane(region='center',overflow='hidden').MDEditor(value='^.mycontent',height='100%',
                                                                   initialEditType='^.initialEditType',
                                                                   previewStyle='^.previewStyle')
