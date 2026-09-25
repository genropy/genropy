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

    def test_2_parametric(self, pane):
        "MDEditor with parameters"
        bc = pane.borderContainer(height='800px',width='600px',border='1px solid silver')
        fb = bc.contentPane(region='top').formbuilder()
        fb.filteringSelect('^.initialEditType',lbl='initialEditType', values='markdown,wysiwyg', default='markdown')
        fb.textbox('^.initialValue',lbl='initialValue', default='This is a **markdown** text')
        fb.filteringSelect('^.previewStyle',lbl='previewStyle', values='tab,vertical', default='tab')
        bc.contentPane(region='center',overflow='hidden').MDEditor(value='^.mycontent',height='100%',
                                                                   initialEditType='^.initialEditType',
                                                                   previewStyle='^.previewStyle', 
                                                                   hideModeSwitch=True, 
                                                                   placeholder='^.initialValue')
        
    def test_3_maxlen(self, pane):
        "MDEditor with maxLength"
        pane.MDEditor(value='^.mycontent.text',height='300px',width='400px',htmlpath='.mycontent.html',
                      maxLength=1024, removeToolbarItems=['image', 'code'])

    def test_4_records(self, pane):
        "Loading a record leaves the datastore untouched: edit A, click outside, load Empty, click Other"
        fb = pane.formbuilder(cols=3)
        fb.button('Record A', action="SET .rec.text='Some **text**'; SET .rec.html='<p>Some <strong>text</strong></p>';")
        fb.button('Empty', action='SET .rec.text=null; SET .rec.html=null;')
        fb.textbox('^.other', lbl='Other')
        pane.MDEditor(value='^.rec.text', htmlpath='.rec.html', height='300px', width='400px',
                      initialEditType='wysiwyg')
        pane.simpleTextArea(value='^.rec.html', readOnly=True, height='60px', width='400px')
