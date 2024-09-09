# -*- coding: utf-8 -*-

"MDEditor"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
        
    def test_0_base(self, pane):
        "Simple MDEditor"
        pane.MDEditor(value='^.mycontent',height='300px',width='400px',htmlpath='.mycontent_html',
                      usageStatistics=True)

    def test_1_viewer(self, pane):
        "MDEditor with viewer"
        pane.data('.mycontent','My *content*')
        pane.MDEditor(value='^.mycontent',height='300px',width='400px',viewer=True)
        #Same result can be achieved with placeholder='My *content*'

    def test_2_parametric(self, pane):
        "MDEditor with parameters"
        bc = pane.borderContainer(height='800px',width='600px',border='1px solid silver')
        fb = bc.contentPane(region='top').formbuilder()
        fb.textbox('^.initialEditType',lbl='initialEditType', values='markdown,wysiwyg')
        fb.textbox('^.initialValue',lbl='initialValue')
        fb.textbox('^.previewStyle',lbl='previewStyle')
        bc.contentPane(region='center',overflow='hidden').MDEditor(value='^.mycontent',height='100%',
                                                                   initialEditType='^.initialEditType',
                                                                   previewStyle='^.previewStyle', 
                                                                   hideModeSwitch=True)
        
    def test_3_maxlen(self, pane):
        "MDEditor with maxLength"
        pane.MDEditor(value='^.mycontent',height='300px',width='400px',htmlpath='.mycontent_html',
                      maxLength=1024, removeToolbarItems=['image', 'code'])