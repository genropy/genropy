# -*- coding: utf-8 -*-

"""dataRemote"""

import datetime
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_dataremote(self, pane):
        """Press button to show time: it shows a different approach from rpc"""
        fb = pane.formbuilder(datapath='test0')
        fb.button('Show time', action='alert(time);', time='=.time')
        fb.dataRemote('.time', self.get_time, cachetime=10)
    
    @public_method
    def rpc_get_time(self, **kwargs):
        return datetime.datetime.now()

    def test_1_datarpc(self, pane):
        """Press button to show seconds: it combines a dataRpc and a dataController 
        dataRpc is used to store value in a path 
        dataController to show alert"""
        pane.button('Show seconds', action='FIRE dammi_ora;')
        pane.dataRpc('.time.seconds', self.get_seconds, _fired='^dammi_ora')
        pane.dataController("alert(seconds)",seconds="^.time.seconds")

    @public_method
    def get_seconds(self, **kwargs):
        return datetime.datetime.now().second

    def test_2_ondiv(self, pane):
        """dataRemote starts automatically triggered by value set by dataFormula"""
        pane = pane.contentPane()
        pane.div('^.quantic_time')
        pane.dataFormula(".quantic_time", "time", time="=.time.seconds", _timing=1)
        pane.dataRemote('.time.seconds', 'get_seconds', cacheTime=10)

    def test_3_params(self, pane):
        "dataRemote triggered by textbox showing given text"
        pane.textbox(value='^.testo')
        pane.div('^.risultato')
        pane.dataRemote('.risultato', self.piero, testo='^.testo')

    @public_method
    def piero(self,testo=None):
        return (testo or 'Ciao')+' Piero'
