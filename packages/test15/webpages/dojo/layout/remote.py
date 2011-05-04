# -*- coding: UTF-8 -*-

# bordercontainer.py
# Created by Francesco Porcari on 2010-08-16.
# Copyright (c) 2010 Softwell. All rights reserved.

"""remote"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    #dojo_theme = 'claro'
    
    def windowTitle(self):
        return 'Remote'
        
    def test_0_bordercontainer_inside_cb(self, pane):
        bc = pane.contentPane(height='200px',background='green').borderContainer(background='red')
        
    def test_1_bordercontainer_cb_splitter(self, pane):
        bc = pane.borderContainer(height='200px')
        bc.contentPane(region='left',width='500px',splitter=True,background='lime').contentPane().remote('xxx',_fired='^aaa')
        bc.contentPane(region='center')
        
    def remote_xxx(self,pane,**kwargs):
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(lbl='aaa')
        fb.textbox(lbl='bbb')
    
    def test_2_jsremote(self,pane,**kwargs):
        pane.button('Remote',action='FIRE .remotetest')
        cp = pane.contentPane(nodeId='test')
        cp.dataController("""
        console.log('call remote_xxx');
        var pane = genro.nodeById('test');
        pane._('div',{remote:{'method':'xxx'}});
        
        """,_fired='^.remotetest')