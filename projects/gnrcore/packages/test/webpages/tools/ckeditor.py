# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_plain(self, pane):
        """ckEditor plain"""
        pane.ckEditor(value='^.text')

    def test_2_constrain(self, pane):
        """ckEditor constrain"""
        fb = pane.formbuilder(cols=2,border_spacing='3px')
        fb.textbox(value='^.height',lbl='Height')
        fb.textbox(value='^.width',lbl='Width')
        pane.ckEditor(value='^.testdata',constrain_height='^.height',
                        config_disableNativeSpellChecker=False,
                        config_stylesSet='/_site/styles/style_pippo.js',
                        constrain_width='^.width',constrain_border='1px solid red')


    def test_3_stylegroup(self, pane):
        """ckEditor stylegroup"""
        fb = pane.formbuilder(cols=2,border_spacing='3px')
        fb.textbox(value='^.height',lbl='Height')
        fb.textbox(value='^.width',lbl='Width')
        pane.ckEditor(value='^.testdata',stylegroup='base',contentsCss='/_rsrc/common/public.css')

    def test_4_quickEditor(self,pane):
        "quickEditor"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.quickEditor(value='^.test',nodeId='aaa',
                        height='100px',
                        width='300px',
                        lbl='test')
        fb.button('focus',action='genro.nodeById("aaa").externalWidget.focus();')
        fb.textbox(value='^.aaa',lbl='field 2')
        fb.textbox(value='^.ooo',lbl='field 3')

    def test_5_simpleTextAreaInGrid(self,pane):
        "quickEditor in grid"
        grid = pane.contentPane(region='center').quickGrid(value='^.griddata',

                        height='500px',width='700px' ,border='1px solid silver',
                        default_description='<span style="color:red">ciao</span> come <i>va?</i>'
                        #connect_onCellDblClick='console.log("sss")'
                        )
        grid.tools('addrow,delrow')
        grid.column('location',name='Location',width='15em',edit=dict(tag='dbselect',dbtable='glbl.provincia'))
        grid.column('description',name='Description',width='30em',edit=dict(tag='quickEditor'))
        grid.column('spam',name='Spam',width='8em',edit=True)