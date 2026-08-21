# -*- coding: utf-8 -*-

"""multibutton"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):

    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
    def windowTitle(self):
        return 'Multibutton test'
        
    def test_0_multibutton_base(self,pane):
        "Values declared inline as a code:caption list, the picked code written into the datastore"
        pane.multibutton(value='^.base',values='pippo:Pippo,paperino:Paperino')
        pane.textbox(value='^.base')
        pane.dataController("genro.bp(true)",v='^.base')

    def test_1_itemsMaxWidth(self,pane):
        "itemsMaxWidth caps the width of the whole item strip, so extra values collapse"
        pane.textbox(value='^.base',lbl='Curr selected')
        pane.textbox(value='^.values',lbl='Curr values',default='pippo:Pippo,pluto:Pluto,paperino:Paperino,mario:Mario,l:luca,c:Cesare,p:Pancrazio,o:Ortensia,a:Antonella,b:Brigitta')
        pane.div(height='20px')
        pane.div(_class='mobile_bar').multibutton(value='^.base',values='^.values',itemsMaxWidth='300px',content_max_width='40px')

    def test_2_multibutton_storepath(self,pane):
        "Items read from a Bag through storepath, inside a slotToolbar slot"
        frame = pane.framePane(frameCode='frameMultibuttonStorepath',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        bar = frame.top.slotToolbar(slots='*,mb,*')

        bar.data('.multibutton.data',self.getmbdata())
        bar.mb.multibutton(value='^.multibutton.value',storepath='.multibutton.data')
        frame.textbox(value='^.multibutton.value')
        frame.textbox(value='^.multibutton.data.pippo?caption')

    def test_3_multibutton_items_path(self,pane):
        "Same Bag passed through items instead of storepath"
        pane.data('.multibutton.data',self.getmbdata())
        pane.multibutton(value='^.base',items='^.multibutton.data')
        pane.textbox(value='^.base')

    def test_4_multibutton_items_struct(self,pane):
        "Items declared one by one, each with its own action, disabled condition or deleteAction"
        pane.checkbox(value='^.disabled')
        mb = pane.multibutton(value='^.base',sticky=False)
        mb.item('pippo',caption='Pippo',disabled='^.disabled',action='alert("Pippo clicked")')
        mb.item('paperino',caption='Paperino',deleteAction='genro.bp(true)')

    def test_5_multibutton_items_delay(self,pane):
        "sticky=False items: one delays its notification, one replaces it with an action of its own"
        pane.dataController("console.log(z);",z='^.base')
        mb = pane.multibutton(value='^.base',sticky=False)

        mb.item('pippo',caption='Pippo')
        mb.item('paperino',caption='Paperino')
        mb.item('delayed',caption='Delayed',_delay=400)
        mb.item('different',caption='Different',action='alert("I am different")')

    def test_6_multibutton_dbstore(self,pane):
        "Items coming from a table, filtered by the province selected in the neighbouring dbselect"
        frame = pane.framePane(frameCode='frameMultibuttonStore',height='400px')
        bar = frame.top.slotToolbar(slots='10,selettore_regione,*,mb,10')
        bar.selettore_regione.dbselect(value='^.regione',dbtable='glbl.regione')
        mb = bar.mb.multibutton(value='^.provincia_selected',caption='nome')
        mb.store(table='glbl.provincia',where='$regione=:reg',reg='^.regione')

    def test_7_multibuttonForm(self,pane):
        "multiButtonForm opened as a remoteDialog: one button per record, each with its own form"
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.button('Remoto',action='genro.dlg.remoteDialog("pr_multi","multibuttonRegione");')
        fb.dbselect(value='^aux.regione',dbtable='glbl.regione',lbl='Regione')

    @public_method
    def multibuttonRegione(self,pane,**kwargs):
        "Content of the remoteDialog of test_7_multibuttonForm"
        bc = pane.borderContainer(height='300px',width='400px',datapath='pippo')
        bc.contentPane(region='center').multiButtonForm(table='glbl.provincia',condition='$regione=:reg',
                                condition_reg='^aux.regione',condition__onBuilt=True,formResource='Form')

    def test_8_multibutton_dbstore_mixed(self,pane):
        "Three multibuttons on one value: sticky items, a table store, and one hidden unless Lazio is picked"
        frame = pane.framePane(frameCode='frameMultibuttonStoreMixed',height='400px')
        bar = frame.top.slotToolbar(slots='10,selettore_regione,*,mb_0,5,mb,5,mb_1,10')
        bar.selettore_regione.dbselect(value='^.regione',dbtable='glbl.regione')
        mb_0 = bar.mb_0.multibutton(value='^.curval',caption='nome',mandatory=False)
        mb_0.item('Pippo',sticky=True)

        mb = bar.mb.multibutton(value='^.curval',caption='nome',mandatory=False)
        mb.store(table='glbl.provincia',where='$regione=:reg',reg='^.regione')

        mb_1 = bar.mb_1.multibutton(value='^.curval',caption='nome',hidden='^.regione?=#v!="LAZ"',mandatory=False)
        mb_1.item('Paperino',sticky=True)

    def getmbdata(self):
        "Bag of code/caption items shared by test_2_multibutton_storepath and test_3_multibutton_items_path"
        result = Bag()
        result.setItem('pippo',None,caption='Pippo')
        result.setItem('pluto',None,caption='Pluto')
        result.setItem('paperino',None,caption='Paperino')
        return result
