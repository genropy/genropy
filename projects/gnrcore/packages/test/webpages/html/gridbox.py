# -*- coding: utf-8 -*-

"Test HTML DIV"
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
                
    def test_0_gridbox(self,pane):
        "Simple"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fc = bc.contentPane(region='center').gridbox(width='400px',height='400px',
                                                     style='grid-template-columns:repeat(4,1fr)',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        for k in range(20):
            fc.div(f'Item {k}',border='1px solid red',margin='5px')


    def test_1_gridbox(self,pane):
        "Simple"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')

        bc.contentPane(region='right',width='100px',splitter=True,background='pink')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^.columns',default='4',lbl='Columns')
        fc = bc.contentPane(region='center').gridbox(width='90%',height='400px',columns='^.columns',column_gap='10px',row_gap='5px',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        fc.div('Item 1',border='1px solid red')
        fc.div('Item 2',style='grid-column:span 2;',border='1px solid green')
        fc.div('Item 3',style='grid-row:span 2;',border='1px solid red')
        fc.div('Item 4',border='1px solid red')
        fc.div('Item 5',border='1px solid red')
        fc.div('Item 6',border='1px solid red')


    def test_2_gridbox(self,pane):
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')

        bc.contentPane(region='right',width='100px',splitter=True,background='pink')

        fc = bc.contentPane(region='center').gridbox(width='90%',height='400px',
                                                     style='grid-template-columns:repeat(4,1fr);column-gap:10px;row-gap:5px;',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        fc.div('Item 2',style='grid-column-start: 2;grid-column-span: 2;grid-row-start: 2; grid-row-span:2;',border='1px solid green')


    def test_3_gridboxform(self,pane):
        fb = pane.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^columns',default='4',lbl='Columns')
    
        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        bc = form.center.borderContainer(datapath='.record')
        bc.contentPane(region='right',splitter=True,width='150px')
        gb = bc.contentPane(region='center').gridbox(columns='^columns',gap='5px')
        side = 'top'
        gb.textbox(value='^.nome',lbl='Nome',lbl_side=side,validate_notnull=True)
        gb.textbox(value='^.cognome',lbl='Cognome',lbl_side=side,validate_notnull=True)
        gb.dateTextBox(value='^.nato_il',lbl='Essendo Nato il',lbl_side=side)
        gb.dbSelect(value='^.provincia_nascita',lbl='Pr.Nascita',table='glbl.provincia',
                        hasDownArrow=True,lbl_side=side)
        gb.textbox(value='^.email',lbl='Email',lbl_side=side,wrp_style='grid-column:span 2;')
        gb.radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',lbl='Genere',lbl_side=side)
        gb.checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance',lbl_side=side)
        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )


    def test_4_gridboxformLabledBox(self,pane):

        fb = pane.gridbox(columns=4,gap='10px',margin='5px',nodeId='boxControllers',datapath='.controllers')
        fb.textBox(value='^.columns',default='3',lbl='Columns')
        fb.filteringSelect(value='^.item_side',lbl='label Side',values='top,left,bottom,right')
        fb.textbox(value='^.item_border',lbl='Item border')
        fb.numberTextBox(value='^.item_rounded',lbl='Rounded')
        fb.input(value='^.item_box_l_background',lbl='Top background',type='color')
        fb.textbox(value='^.item_box_c_padding',lbl='Content Padding')
        fb.textbox(value='^.item_fld_border',lbl='Field border')
        fb.textbox(value='^.item_fld_background',lbl='Field background')



        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        bc = form.center.borderContainer(datapath='.record')
        bc.contentPane(region='right',splitter=True,width='150px')
        gb = bc.contentPane(region='center').gridbox(columns='^#boxControllers.columns',gap='10px',margin='20px',
                                                     item_border='^#boxControllers.item_border',
                                                     item_side='^#boxControllers.item_side',
                                                     item_rounded='^#boxControllers.item_rounded',
                                                     item_fld_border='^#boxControllers.item_fld_border',
                                                    item_fld_background='^#boxControllers.item_fld_background',
                                                     item_box_l_background='^#boxControllers.item_box_l_background',
                                                     item_box_c_padding='^#boxControllers.item_box_c_padding')
        gb.labledBox('Nome',helpcode='bbb').textbox(value='^.nome',validate_notnull=True)
        gb.labledBox('Cognome',helpcode='aaa').textbox(value='^.cognome',validate_notnull=True)
        gb.labledBox('Genere',rowspan=2).radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',cols=1)

        gb.labledBox('Essendo Nato il').dateTextBox(value='^.nato_il')
        gb.labledBox('Pr.Nascita').dbSelect(value='^.provincia_nascita',table='glbl.provincia',
                        hasDownArrow=True)
        gb.labledBox('Privacy acceptance').checkbox(value='^.privacy',label='Accept')

        gb.labledBox('Email',colspan=2).textbox(value='^.email')

        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )




    def test_5_gridbox_structpath(self,pane):
        bc = pane.borderContainer(height='500px',width='500px')
        pane =  bc.contentPane(region='center')
        gb =pane.gridbox(columns=2,items='^.items',
                          border='2px solid silver',
                          padding='10px',margin='10px')
        gb.radioButtonText(value='^.genere',values='M:Maschio,F:Femmina',cols=2,lbl='Genere',colspan=2)
        gb.textbox(value='^.nome',lbl='Nome')
        gb.textbox(value='^.cognome',lbl='Cognome').comboArrow(nodeId='alfredo')


    
    def test_6_gridbox_inside(self,pane):
        pane.button('Set source').dataController("SET .items=source;",source='=.test_from_source')
        pane.button('Set bag').dataController("SET .items=source;",source='=.test_from_bag')
        pane.br()
        pane.gridbox(cols=2,items='^.items',lbl='Dati anagrafici')
        pane.data('.test_from_source',self.contentAnagrafica())
        pane.data('.test_from_bag',self.contentAnagrafica_bag())
        

    
    def contentAnagrafica_bag(self):
        result = Bag()
        result.addItem('item_0',None,tag='textbox',value='^.nome',lbl='Nome da bag')
        result.addItem('item_1',None,tag='textbox',value='^.cognome',lbl='Cognome da bag')
        return result

    def contentAnagrafica(self):
        pane = self.newSourceRoot()
        pane.textbox(value='^.nome',lbl='Nome')
        pane.textbox(value='^.cognome',lbl='Cognome')
        return pane
    


    def test_7_gridbox_hiddenElementsFormula(self,pane):
        gb = pane.gridbox(columns=2)
        gb.checkbox(value='^.check_1',lbl='Check 1')
        gb.checkbox(value='^.check_2',lbl='Check 2')
        gb.textbox(value='^.nascondimi',hidden='==_check_1 && _check_2',
                   _check_1='^.check_1', _check_2='^.check_2',lbl='Ciao')
