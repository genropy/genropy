# -*- coding: utf-8 -*-

"""dataRpc"""

import psutil
import datetime
from time import sleep
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_datarpc(self, pane):
        """Press button to show seconds: it combines a dataRpc and a dataController 
        dataRpc is used to store value in a path 
        dataController to show alert"""
        pane.button('Show seconds', action='FIRE dammi_ora;')
        pane.dataRpc('.time.seconds', self.get_seconds, _fired='^dammi_ora')
        pane.dataController("alert(seconds)",seconds="^.time.seconds")

    @public_method
    def get_seconds(self, **kwargs):
        return datetime.datetime.now().second

    def test_1_nested(self, pane):
        """Nested syntax: dataRpc can be attached to button. Result is the same but syntax is simpler"""
        btn = pane.button('Show seconds')
        btn.dataRpc('.time.seconds', self.get_seconds)
        pane.div('^.time.seconds')

    def test_2_simplesum(self, pane):
        "dataRpc can be triggered by value insertion. Insert numbers and push tab"
        fb = pane.formbuilder(cols=3, fld_width='5em')
        #initialize fields
        fb.data('.first_term',0)
        fb.data('.second_term',0)
        
        fb.numbertextbox('^.first_term', lbl='First term')
        fb.numbertextbox('^.second_term', lbl='Second term')
        fb.numbertextbox('^.result', readOnly=True)
        
        #parameters triggers the rpc when they are updated
        fb.dataRpc('.result', self.simplesum, first='^.first_term', second='^.second_term')
    
    @public_method
    def simplesum(self, first, second):
        return first + second

    def test_3_cputimes(self,root,**kwargs):
        "dataRpc can be triggered automatically on start and execute every n seconds"
        root.h1('Cpu Times',text_align='center',color='888')   
        pane=root.div(margin='15px',datapath='cpuTimes')
        pane.quickGrid(value='^.data', border='1px solid silver',
                              font_family='courier',font_weight='bold',
                              height='auto',width='auto')
        pane.dataRpc('.data', self.getCpuTimes, _timing=1,_onStart=True)
 
    @public_method
    def getCpuTimes(self):
        result=Bag()
        columns=['user','nice','system','idle']
        for j, core in enumerate(psutil.cpu_times(True)):
            row = Bag()
            row['core']=j+1
            for k in columns:
                row.setItem(k, getattr(core,k))
            result.setItem('r_%i'%j, row)
        return result

    def test_4_long_thermo(self,pane):
        "Insert number of records and pause, progress will be shown"
        pane.numberTextBox(value='^.numero',lbl='Numero')
        pane.numberTextBox(value='^.pausa',lbl='Pausa')

        pane.button('Procedi',fire='.procedi')
        pane.dataRpc(None,self.rpcConTermometro,
                    _fired='^.procedi',
                    numero='=.numero',
                    pausa='=.pausa',
                    _lockScreen=dict(thermo=True))

    @public_method
    def rpcConTermometro(self,numero=None,pausa=None):
        numero = numero or 20
        pausa = pausa or .5
        lista= ['Numero {i}'.format(i=i) for i in range(numero)]
        for elem in self.utils.quickThermo(lista,labelfield='prova'):
            self.log(elem)
            sleep(pausa)

    def test_5_ask(self, pane):
        "Parameters can be asked during rpc call and parameters are automatically sent to rpc method"
        fb = pane.formbuilder(cols=1)
        btn = fb.button('How many days left to your birthday?')
        btn.dataRpc('.days_left', self.getTime, _ask=dict(title='When is your next birthday?', 
                                    fields=[dict(name='birthday', tag='datetextbox', lbl='Date')]))
        fb.div('^.days_left', lbl='Days left')

    @public_method
    def getTime(self, birthday=None):
        today = datetime.today().date()
        days_left = birthday - today
        return str(days_left)
