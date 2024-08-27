# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
                
    def test_0_flex(self,pane):
        "Boxes with flex. Specify direction and wrap"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.filteringSelect(value='^.direction',values='row,column,row-reverse,column-reverse')
        fb.checkbox(value='^.wrap',label='Wrap')

        fc = bc.contentPane(region='center').flexbox(direction='^.direction',wrap='^.wrap',width='300px',
                                                     height='400px',border='1px solid silver',padding='5px',
                                                     margin='5px')
        for k in range(20):
            fc.div(f'Item {k}',border='1px solid red',height='40px',width='40px',margin='5px')


    def test_1_2dtable(self,pane):
        "Boxes with flex. Specify direction and wrap"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.filteringSelect(value='^.direction',values='row,column,row-reverse,column-reverse',default='row')
        fb.filteringSelect(value='^.inner_direction',values='row,column,row-reverse,column-reverse',default='column')

        fb.checkbox(value='^.wrap',label='Wrap')

        fc = bc.contentPane(region='center').flexbox(direction='^.direction',wrap='^.wrap',width='300px',
                                                     height='400px',border='1px solid silver',padding='5px',
                                                     margin='10px')
        for j in range(5):
            innertFc = fc.flexbox(direction='^.inner_direction',
                                  flex_basis='100px',margin='5px',border='1px solid pink',
                                )
            for k in range(5):
                innertFc.div(f'Item {k}',border='1px solid red',flex_basis='10px',
                             margin='2px')


    def test_3_2dtable(self,pane):
        "Boxes with flex. Specify direction and wrap"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.filteringSelect(value='^.direction',values='row,column,row-reverse,column-reverse',default='row')
        fb.filteringSelect(value='^.inner_direction',values='row,column,row-reverse,column-reverse',default='column')

        fb.checkbox(value='^.wrap',label='Wrap')
        pane = bc.contentPane(region='center')
        extflex = pane.flexbox(diretion='row',position='absolute',top='0',left='0',right='0',bottom='0')
        
        fc = extflex.flexbox(direction='^.direction',wrap='^.wrap',width='300px',
                                                     height='400px',border='1px solid silver',padding='5px',
                                                     margin='10px')
        for j in range(5):
            innertFc = fc.flexbox(direction='^.inner_direction',
                                  flex_basis='100px',margin='5px',border='1px solid pink',
                                )
            for k in range(5):
                innertFc.div(f'Item {k}',border='1px solid red',flex_basis='10px',
                             margin='2px')
        fc = extflex.flexbox(direction='^.direction',wrap='^.wrap',width='300px',
                                                     height='400px',border='1px solid silver',padding='5px',
                                                     margin='10px')
        for j in range(5):
            innertFc = fc.flexbox(direction='^.inner_direction',
                                  flex_basis='100px',margin='5px',border='1px solid pink',
                                )
            for k in range(5):
                innertFc.div(f'Item {k}',border='1px solid red',flex_basis='10px',
                             margin='2px')
