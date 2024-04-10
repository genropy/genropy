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
                                                                                            
    #DP Doesn't work requires to be updated
    #def test_3_gallery_handler(self,pane):
    #    "Image palette to drag and drop images into editor"
    #    frame = pane.framePane(height='300px')
    #    bar = frame.top.slotToolbar('*,imgpal,5')
    #    bar.dataFormula('^testpath','p',_onStart=True,p='')
    #    bar.imgpal.imgPickerPalette(folders='rsrc:common/html_pages/images:Image HTML',dockButton=True) 
    #    frame.center.contentPane(overflow='hidden').ckEditor(value='^.testgallery')

    def test_3_simpleTextAreaEditor(self,pane):              
        "Quick editor version in external palette"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.simpleTextArea(value='^.test', height='100px', width='300px', lbl='test', editor=True)

    def test_4_quickEditor(self,pane):              
        "Quick editor version in external palette"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.quickEditor(value='^.test',nodeId='aaa',
                        height='100px',
                        width='300px',
                        lbl='test')
        fb.button('focus',action='genro.nodeById("aaa").externalWidget.focus();')
        fb.textbox(value='^.other_field',lbl='Other field')

    def test_5_inline_edit(self,pane):                 #DP Da sistemare, qui proviamo la floating toolbar
        "Inline edit can be used to show a minimal toolbar while writing instead"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        pass

    def test_6_simpleTextAreaInGrid(self,pane):
        "Editor used in grid"
        grid = pane.contentPane(region='center').quickGrid(value='^.griddata',
                        height='500px',width='700px' ,border='1px solid silver',
                        default_description='<span style="color:red">Hi there</span> come <i>va?</i>'
                        #connect_onCellDblClick='console.log("sss")'
                        )
        grid.tools('addrow,delrow')
        grid.column('location',name='Location',width='15em',edit=dict(tag='dbselect',dbtable='glbl.provincia'))
        grid.column('description',name='Description',width='30em',edit=dict(tag='quickEditor'))
        grid.column('spam',name='Spam',width='8em',edit=True)
