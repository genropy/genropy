# -*- coding: utf-8 -*-

"""Buttons"""
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_alert(self,pane):
        pane.button('Hello',action='alert(message)',message='Hello')
        pane.button('Hello again').dataController('alert(message);',message='Hello')

    def test_2_ask(self,pane):
        pane.data('.pars.color','red')
        pane.data('.pars.size','18px')

        pane.textbox(value='^.cognome',lbl='Cognome',default='Bianchi')
        
        pane.button('Hello again').dataController('genro.dlg.alert(message + cognome + color + size,"Pippo")',message='Hello ',
                                                cognome='=.cognome',
                                                color='=.pars.color',
                                                size='=.pars.size',
                                                _ask=dict(title='Complete parameters',_if='!color || !size || _filterEvent("Shift")',
                                                            fields=[dict(name='color',lbl='Color'),
                                                                    dict(name='size',lbl='Size')]))


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
        m.menuline('Azione 2').dataRpc(self.db.table('fatt.fattura').testRpc,
                    _ask=dict(title='Confirm',
                              fields=[
                                dict(name='pkey', lbl='Shipment', validate_notnull=True),
                                dict(name='codice', lbl='Proforma Type', hasDownArrow=True, validate_notnull=True)
                              ]
                             ),
                    _onResult="""
                        alert('Creata la fatt. proforma '+result.getItem('protocollo'));
                    """
            )
        m.menuline('Azione 3')


    @public_method
    def testRpc(self,cognome=None,**kwargs):
        print(x)