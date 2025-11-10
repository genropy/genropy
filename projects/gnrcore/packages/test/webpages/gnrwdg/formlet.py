
class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                th/th:TableHandler"""
                

    def test_1_helpbox(self,pane):
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
