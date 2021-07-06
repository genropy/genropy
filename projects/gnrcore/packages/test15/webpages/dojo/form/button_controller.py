# -*- coding: utf-8 -*-

"""Buttons"""
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_alert(self,pane):
        pane.button('Hello',action='alert(message)',message='Hello')
        pane.button('Hello again').dataController('alert(message);',message='Hello')

    def test_2_ask(self,pane):
        pane.button('Hello again').dataController('genro.bp(true);alert(message + cognome)',message='Hello ',
                                                cognome='Bianchi',
                                                _ask=dict(title='Complete parameters',
                                                            fields=[dict(name='cognome',lbl='Cognome')]))


    def test_3_dataRpc(self,pane):
        rpc = pane.button('Run on server').dataRpc(self.testRpc,
                                                _ask=dict(title='Complete parameters',
                                                fields=[dict(name='cognome',lbl='Cognome')]))


    @public_method
    def testRpc(self,cognome=None,**kwargs):
        print(x)