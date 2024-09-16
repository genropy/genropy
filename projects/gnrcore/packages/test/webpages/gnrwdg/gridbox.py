# -*- coding: utf-8 -*-

"Test HTML DIV"
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
                
    def test_0_gridbox(self,pane):
        "Simple fixed gridbox"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fc = bc.contentPane(region='center').gridbox(width='400px',height='400px',
                                                     style='grid-template-columns:repeat(4,1fr)',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        for k in range(20):
            fc.div(f'Item {k}',border='1px solid red',margin='5px')

    def test_1_gridbox(self,pane):
        "Simple gridbox, specify number of columns"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')

        bc.contentPane(region='right',width='100px',splitter=True,background='pink')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^.columns',default='4',lbl='Columns')
        fc = bc.contentPane(region='center').gridbox(width='90%',item_height='100px',columns='^.columns',column_gap='10px',row_gap='5px',
                                                     border='1px solid silver',padding='5px',item_border='1px solid red',
                                                     margin='5px')
        fc.div('Item 1')
        fc.div('Item 2',colspan=2,border='1px solid green')
        fc.div('Item 3',rowspan=2,height='100%')
        fc.div('Item 4')
        fc.div('Item 5')
        fc.div('Item 6')


    def test_2_gridbox(self,pane):
        "Simple gridbox, only one centered item"
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        bc.contentPane(region='right',width='100px',splitter=True,background='pink')
        fc = bc.contentPane(region='center').gridbox(width='90%',height='400px',
                                                     style='grid-template-columns:repeat(4,1fr);column-gap:10px;row-gap:5px;',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        fc.div('Item 2',style='grid-column-start: 2;grid-column-span: 2;grid-row-start: 2; grid-row-span:2;',border='1px solid green')


    def test_3_gridboxform(self,pane):
        "Gridbox can be used instead of formbuilder, with more control on layout"
        fb = pane.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^columns',default='4',lbl='Columns')
    
        form = pane.frameForm(frameCode='TestForm3',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
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

    def test_4_gridboxLabledBox(self,pane):
        "Labels, rounded, border, background, padding attributes can be specified"
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').gridbox(columns=4,gap='10px',margin='5px',nodeId='boxControllers',datapath='.controllers')
        fb.textBox(value='^.columns',default='3',lbl='Columns')
        fb.filteringSelect(value='^.item_side',lbl='label Side',values='top,left,bottom,right')
        fb.textbox(value='^.item_border',lbl='Item border')
        fb.numberTextBox(value='^.item_rounded',lbl='Rounded')
        fb.input(value='^.item_box_l_background',lbl='Top background',type='color')
        fb.textbox(value='^.item_box_c_padding',lbl='Content Padding')
        fb.textbox(value='^.item_fld_border',lbl='Field border')
        fb.textbox(value='^.item_fld_background',lbl='Field background')

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

        gb.textbox(value='^.email',lbl='Email',colspan=2)