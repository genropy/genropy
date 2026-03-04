# -*- coding: utf-8 -*-

"""Serverpath"""

from gnr.core.gnrbag import DirectoryResolver

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
   
    def test_0_tree(self, pane):
        "Basic tree built on cities table"
        pane.dataRemote('.store',self.relationExplorer,table='glbl.provincia',currRecordPath='record')
        pane.tree('.store',hideValues=True)
    
    def test_1_checkboxtree(self,pane,**kwargs):
        "Basic checkbox tree: check directories "
        bc=pane.borderContainer(height='500px')
        self.treePane(bc.contentPane(region='left',splitter=True,
                                     width='250px',padding='4px'))    
        center=bc.contentPane(region='center')
        right=bc.contentPane(region='right',width='300px',splitter=True)
        center.simpleTextArea(value='^.checked',font_size='.9em',height='100%')
        right.pre(value='^.checked_abspath',font_size='.9em',height='100%')
        
    def treePane(self,pane):
        resolver= DirectoryResolver('/')
        pane.data('.root.genropy',resolver())
        pane.tree(storepath='.root',hideValues=True,autoCollapse=True,
                      checkChildren=True,checkedPaths='.checked',checkedPaths_joiner='\n',
                      labelAttribute='nodecaption')

    def test_2_treegrid(self,pane):
        "Basic treegrid with directories, with styles"
        resolver= DirectoryResolver('/users')
        pane.data('.root.genropy',resolver())
        bc = pane.borderContainer(height='300px',width='600px')
        tg = bc.contentPane(region='center').treeGrid(storepath='.root.genropy',headers=True)
        tg.column('nodecaption',header='Name')
        tg.column('file_ext',size=50,header='Ext')
        tg.column('size',size=50,header='Size',dtype='L')

    def test_3_treegrid(self,pane):
        "Same as before, but without styles"
        resolver= DirectoryResolver('/users')
        pane.data('.root.genropy',resolver())
        box=pane.div(height='400px',margin='60px',border='1px solid silver',position='relative')
        box.tree(storepath='.root.genropy',_class='branchtree noIcon')  

    def test_4_tree_searchOn(self,pane):
        "Tree with searchOn to perform a research"
        pane.dataRemote('.tree',self.relationExplorer,table='glbl.provincia',omit='_*',
                        z_resolved=True)
    
        pane.div(height='400px').tree(storepath='.tree',_class="branchtree noIcon",hideValues=True,autoCollapse=True,
                    height='200px',
                    width='300px',
                    border='1px solid #efefef',
                    searchOn=True
                    )
        
    def test_5_tree_popup(self,pane):
        "Tree with a popup"
        pane.dataRemote('.tree',self.relationExplorer,table='glbl.provincia',omit='_*',
                        z_resolved=True)
    
        pane.div(height='20px',width='20px',
                    background='green',margin='20px'
                    ).tree(storepath='.tree',popup=dict(closeEvent='onClick'))