# -*- coding: utf-8 -*-

"Test HTML DIV"

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

        gb.labelBox('Pippo').textBox()
        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )

    def test_4_labledBox(self,pane):
        pane.labledBox(label='Pippo',side='top',helpcode='uuu',label_color='green',label_font_size='16px',
                       box_l_background='orange',
                       padding='10px',border='1px solid silver').textBox(value='^.pippo')

        pane.labledBox(label='Pluto',side='top',
                       padding='10px',border='1px solid green',
                       moveable=True).simpleTextArea(value='^.paperino',height='200px',width='400px')
