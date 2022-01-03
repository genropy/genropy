# -*- coding: utf-8 -*-

# Created by Francesco Porcari on 2010-08-16 and updated by Davide Paci on 2021-12-27.
# Copyright (c) 2010 Softwell. All rights reserved.

from gnr.core.gnrdecorator import public_method
from time import sleep

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
        
    def test_0_bordercontainer_cb_splitter(self, pane):
        "Use remote to define content in a separate method"
        bc = pane.borderContainer(height='150px')
        bc.contentPane(region='left',width='500px',splitter=True,background='lime').remote(self.remoteMethod)
        bc.contentPane(region='center')
        
    @public_method
    def remoteMethod(self,pane,**kwargs):
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(lbl='aaa')
        fb.textbox(lbl='bbb')
    
    def test_1_jsremote(self,pane,**kwargs):
        "Dynamic content area using a dataController"
        pane.button('Remote').dataController("""
        console.log('call remote_xxx');
        var pane = genro.nodeById('test');
        pane._('div',{remote:{'method':'xxx'},min_height:'1px'});""")
        pane.contentPane(nodeId='test')
        pane.button('Clear').dataController("""
        var pane = genro.nodeById('test');
        pane.clearValue();""")

    def test_2_remote_params(self, pane):
        "Remote content triggered by dbSelect"
        bc = pane.borderContainer(height='150px')
        fb = bc.contentPane(region='top').formbuilder(cols=1)
        fb.dbSelect(value='^.state', table='glbl.regione', lbl='State', hasDownArrow=True)
        bc.contentPane(region='center').remote(self.blocchiProvincia, state='^.state')
    
    @public_method
    def blocchiProvincia(self,pane,state=None,**kwargs):
        if not state:
            pane.div('Please choose a state')
            return
        tab = pane.tabContainer(margin='2px')
            
        province = self.db.table('glbl.provincia').query(where='$regione=:reg',reg=state).fetch()
        for pr in province:
            paneProv = tab.contentPane(title=pr['nome'])
            fb = paneProv.formbuilder(datapath=f'.{pr["sigla"]}')
            fb.radioButtonText(value='^.been_there',lbl='Have you ever been there?', values='Y:Yes,N:No')
            fb.textbox(value='^.review', lbl='How was your trip?', disabled='^.been_there?=#v=="N"')

    def test_3_remoteLazy(self, pane):
        "Remote lazy triggered on click, using sleep"
        tc = pane.tabContainer(height='150px')
        tc.contentPane(title='Page 1').simpleTextArea(value='^.text')
        tc.contentPane(title='Page 2').remote(self.paginaLazy,_waitingMessage='Please wait')
    
    @public_method
    def paginaLazy(self,pane):
        sleep(3)
        pane.div('Remote content with lazy loading', margin='10px')
