# -*- coding: utf-8 -*-

"""Buttons"""
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_alert(self,pane):
        pane.button('Hello',action='alert(message)',message='Hello')
        pane.button('Hello again').dataController('alert(message);',message='Hello')

    def test_2_ask(self,pane):
        pane.textbox(value='^.cognome',lbl='Cognome',default='Bianchi')
        pane.button('Hello again').dataController('alert(message + cognome)',message='Hello ',
                                                cognome='=.cognome',
                                                _ask=dict(title='Complete parameters',_if='!cognome',
                                                            fields=[dict(name='cognome',lbl='Cognome')]))


    def test_3_dataRpc(self,pane):
        rpc = pane.button('Run on server').dataRpc(self.testRpc,
                                                _ask=dict(title='Complete parameters',
                                                fields=[dict(name='cognome',lbl='Cognome')]))

    def test_3_menu(self,pane):
        m = pane.menudiv(iconClass='iconbox gear')
        m.menuline('Azione 1').dataController('alert(message + cognome)',message='Hello ',
                                                cognome='Pippone',
                                                _ask=dict(title='Complete parameters',
                                                            fields=[dict(name='cognome',lbl='Cognome')]))
        m.menuline('Azione 2')
        m.menuline('Azione 3')


    @public_method
    def testRpc(self,cognome=None,**kwargs):
        print(x)