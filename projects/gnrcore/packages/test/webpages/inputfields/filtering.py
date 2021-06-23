# -*- coding: utf-8 -*-

"filteringSelect and comboBox"

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'filteringSelect and comboBox'

    def isDeveloper(self):
        return True
         
    def test_0_filtering(self,pane):
        "Basic filteringSelect. Choose between available values, then press reset to clear values"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.data('.code','1')
        fb.filteringSelect(value='^.code',values='0:Zero,1:One,2:Two',lbl='With code')
        fb.filteringSelect(value='^.description',values='Zero,One,Two',lbl='No code')
        fb.button('Reset values',action='SET .code=null;SET .description=null')

    def test_1_filtering(self,pane):
        "Basic filteringSelect, list of values built as Bag"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        b = Bag()
        b.setItem('r1',None,caption='Foo',id='A')
        b.setItem('r2',None,caption='Bar',id='B')
        b.setItem('r3',None,caption='Spam',id='C')
        fb.data('.store',b)
        fb.filteringSelect(value='^.tbag',lbl='Test bag 1',storepath='.store')

    def test_2_combobox(self,pane):
        "Basic comboBox. Choose values or manually insert a new one."
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.comboBox(value='^.description',values='Zero,One,Two',lbl='Combo')

    def test_3_filtering(self,pane):
        "Same list of values built as Bag, but store is built with keys"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        b = Bag()
        b.setItem('A',None,caption='Foo')
        b.setItem('B',None,caption='Bar')
        b.setItem('C',None,caption='Spam')
        fb.data('.store',b)
        fb.filteringSelect(value='^.tbag',lbl='Test bag 3',storepath='.store',
                            storeid='#k')  

    def test_4_filteringCombo(self, pane):
        "filteringSelect vs comboBox: in comboBox you can choose values even not suggested values. Displayed value vs real value"
        fb=pane.formbuilder(cols=2)
        fb.filteringSelect(lbl='filteringSelect',value='^.filtering',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.comboBox(lbl='comboBox',value='^.combobox',values='PI:Pippo,PL:Pluto,PA:Paperino')
        fb.div('^.filtering')
        fb.div('^.combobox')

