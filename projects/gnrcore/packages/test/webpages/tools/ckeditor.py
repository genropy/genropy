# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase,public:Public,gnrcomponents/filepicker:FilePicker"
                    
    def test_1_constrain(self, pane):
        "You can set inner text dimensions using constrain"
        fb = pane.formbuilder(cols=2,border_spacing='3px')
        fb.textbox(value='^.height',lbl='Height')
        fb.textbox(value='^.width',lbl='Width')
        pane.ckeditor(value='^.testdata', constrain_height='^.height',
                        config_disableNativeSpellChecker=False,
                        config_stylesSet='/_site/styles/style_pippo.js',
                        constrain_width='^.width', constrain_border='1px solid red')

    def test_2_toolbar(self, pane):                             
        "Toolbar can be simple or standard and can be hidden"
        pane.ckEditor(value='^.testdata', toolbar='standard', 
                                            config_toolbarCanCollapse=True)    
                                                                                            

    def test_3_gallery_handler(self,pane):
        "Image palette to drag and drop images into editor"
        frame = pane.framePane(height='300px')
        bar = frame.top.slotToolbar('*,xxx,5')
        bar.dataFormula('^testpath','p',_onStart=True,p='')
        bar.xxx.imgPickerPalette(folders='rsrc:common/html_pages/images:Image HTML,rsrc:common/icons:Icons',dockButton=True)
        frame.center.contentPane(overflow='hidden').ckEditor(value='^.testgallery')

    def test_4_simpleTextAreaEditor(self,pane):                 #DP Da sistemare
        "Quick editor version"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.quickEditor(value='^.test',nodeId='aaa',
                        height='100px',
                        width='300px',
                        lbl='test')
        fb.button('focus',action='genro.nodeById("aaa").externalWidget.focus();')
        fb.textbox(value='^.aaa',lbl='field 2')
        fb.textbox(value='^.ooo',lbl='field 3')

    def test_5_simpleTextAreaEditor(self,pane):                 #DP Da sistemare, qui proviamo la floating toolbar
        "Floating toolbar"
        pane.div(_class='quickEditor',height='100px',width='400px').ckEditor(value='^.ccc',
                    constrain_margin_top='1px',
                    constrain_margin='2px',
                    toolbar=False)

    def test_6_simpleTextAreaInGrid(self,pane):
        grid = pane.contentPane(region='center').quickGrid(value='^.griddata',
                        height='500px',width='700px' ,border='1px solid silver',
                        default_description='<span style="color:red">ciao</span> come <i>va?</i>'
                        #connect_onCellDblClick='console.log("sss")'
                        )
        grid.tools('addrow,delrow')
        grid.column('location',name='Location',width='15em',edit=dict(tag='dbselect',dbtable='glbl.provincia'))
        grid.column('description',name='Description',width='30em',edit=dict(tag='quickEditor'))
        grid.column('spam',name='Spam',width='8em',edit=True)
