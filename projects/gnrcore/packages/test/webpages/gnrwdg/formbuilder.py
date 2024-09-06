# -*- coding: utf-8 -*-

"""Formbuilder"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_htmltable(self, pane):
        "Formbuilder is basically an HTML table"
        t = pane.table(style='border-collapse:collapse',border='1px solid silver').tbody()
        r = t.tr()
        r.td(width='100%')
        r.td(width='50%').div('Pippo')
        r.td(width='50%').div('Pluto')

        fb = pane.formbuilder(cols=2,border_spacing='3px',border='1px solid silver',colswidth='auto')
        fb.div('Pippo',lbl='Alfa')
        fb.div('Pluto',lbl='Beta')

    def test_1_basic(self, pane):
        "Formbuilder with basic widgets: use of textbox, readOnly and data"
        fb = pane.formbuilder(cols=2, border_spacing='10px', fld_width='100%')
        fb.textbox(value='^.aaa', lbl='Textbox')
        fb.data('.bb','piero')
        fb.textbox(value='^.bb', lbl='readOnly',readOnly=True)
        fb.textbox(value='^.cc', lbl='Bigger textbox', colspan=2)
        
        b = Bag()
        b.setItem('foo',None,id='foo',caption='Foo',test='AAA')
        b.setItem('bar',None,id='bar',caption='Bar',test='BBB')
        b.setItem('spam',None,id='spam',caption='Spam',test='CCC')
        
        fb.data('.xxx',b)
        fb.combobox(value='^.ttt',lbl='Combobox',width='10em',storepath='.xxx',selected_test='.zzz')
        fb.div('^.zzz')

    def test_1M_basic(self, pane):
        "Formbuilder with basic widgets: use of textbox, readOnly and data"
        fb = pane.formbuilder(cols=2, border_spacing='2px', fld_width='100%',boxMode=True,lblclass=None)
        fb.textbox(value='^.short_text', lbl='Shortname',validate_len='0:5')
        fb.data('.bb','piero')
        fb.textbox(value='^.bb', lbl='readOnly',readOnly=True)
        fb.textbox(value='^.cc', lbl='Bigger textbox', colspan=2,width='30em')
        fb.radioButtonText(value='^.sex',values='M:Male,F:Female',lbl='Sex')
        fb.checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance')

        b = Bag()
        b.setItem('foo',None,id='foo',caption='Foo',test='AAA')
        b.setItem('bar',None,id='bar',caption='Bar',test='BBB')
        b.setItem('spam',None,id='spam',caption='Spam',test='CCC')
        
        fb.data('.xxx',b)
        fb.combobox(value='^.ttt',lbl='Combobox',width='10em',storepath='.xxx',selected_test='.zzz')
        fb.div('^.zzz')


    def test_1Z_basic(self, pane):
        pane.textbox(value='^.left',lbl='Test L',lbl_side='left')
        pane.textbox(value='^.top',lbl='Test T',lbl_side='top')
        pane.textbox(value='^.right',lbl='Test R',lbl_side='right')
        pane.textbox(value='^.bottom',lbl='Test B',lbl_side='bottom')


    def test_2Z_testForm(self, pane):
        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        t = form.record.table(border_spacing='8px',margin='20px').tbody()
        r = t.tr()
        r.td().textbox(value='^.nome',lbl='Nome',validate_notnull=True)
        r.td().textbox(value='^.cognome',lbl='Cognome',validate_notnull=True)
        r = t.tr()
        r.td().dateTextBox(value='^.nato_il',lbl='Nato il')
        r.td().dbSelect(value='^.provincia_nascita',lbl='Pr.Nascita',table='glbl.provincia',hasDownArrow=True)
        r = t.tr()
        r.td(colspan=2).textbox(value='^.email',lbl='Email',width='30em')
        r = t.tr()
        r.td().radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',lbl='Genere')
        r.td().checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance')
        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )

    def test_2K_testForm(self, pane):
        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        t = form.record.table(border_spacing='8px',margin='20px').tbody()
        r = t.tr()
        side = 'top'
        r.td().textbox(value='^.nome',lbl='Nome',helpcode='nome',lbl_side=side,validate_notnull=True)
        r.td().textbox(value='^.cognome',lbl='Cognome',lbl_side=side,validate_notnull=True)
        r = t.tr()
        r.td().dateTextBox(value='^.nato_il',lbl='Essendo Nato il',lbl_side=side)
        r.td().dbSelect(value='^.provincia_nascita',lbl='Pr.Nascita',table='glbl.provincia',
                        hasDownArrow=True,lbl_side=side)
        r = t.tr()
        r.td(colspan=2).textbox(value='^.email',lbl='Email',width='30em',lbl_side=side)
        r = t.tr()
        r.td().labledbox(side=side,label='Genere').radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro')
        r.td().checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance',lbl_side=side)
        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )




    def test_2FLEX_testForm(self, pane):
        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        bc = form.center.borderContainer(datapath='.record')
        bc.contentPane(region='right',splitter=True,width='150px')
        r = bc.contentPane(region='center').div(style='display:flex;flex-wrap:wrap;',margin='5px')
        side = 'top'
        r.textbox(value='^.nome',lbl='Nome',lbl_side=side,validate_notnull=True,sss=33) #helpcode='nome'
        r.textbox(value='^.cognome',lbl='Cognome',lbl_side=side,validate_notnull=True)
        r.dateTextBox(value='^.nato_il',lbl='Essendo Nato il',lbl_side=side)
        r.dbSelect(value='^.provincia_nascita',lbl='Pr.Nascita',table='glbl.provincia',
                        hasDownArrow=True,lbl_side=side)
        r.textbox(value='^.email',lbl='Email',width='30em',lbl_side=side)
        r.radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',lbl='Genere',lbl_side=side)
        r.checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance',lbl_side=side)
        bar = form.bottom.slotBar('*,confirm,5')
        bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )

    def test_3FLEX_random(self, pane):
        import random
        form = pane.frameForm(frameCode='TestForm',datapath='.mieidati',store='memory',height='500px',border='1px solid silver',rounded=10)
        bc = form.center.borderContainer(datapath='.record')
        bc.contentPane(region='right',splitter=True,width='150px')
        r = bc.contentPane(region='center').div(style='display:flex;flex-wrap:wrap;justify-content:stretch;')
        side = 'top'
        for j in range(30):
            r.textbox(value=f'^.field_{j}',lbl=f'Field {j}',lbl_side=side,
                      width=f'{random.randint(8,20)}em')

       #r.textbox(value='^.cognome',lbl='Cognome',lbl_side=side,validate_notnull=True)
       #r.dateTextBox(value='^.nato_il',lbl='Essendo Nato il',lbl_side=side)
       #r.dbSelect(value='^.provincia_nascita',lbl='Pr.Nascita',table='glbl.provincia',
       #                hasDownArrow=True,lbl_side=side)
       #r.textbox(value='^.email',lbl='Email',width='30em',lbl_side=side)
       #r.radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',lbl='Genere',lbl_side=side)
       #r.checkbox(value='^.privacy',label='Accept',lbl='Privacy acceptance',lbl_side=side)
       #bar = form.bottom.slotBar('*,confirm,5')
       #bar.confirm.button('Save',action='alert(this.form.getFormData().toXml())')
        pane.dataController("frm.newrecord();",
            frm=form.js_form,
            _onStart=True
        )
    def test_2LABELCONT_aaa(self, pane):
        tc = pane.tabContainer(height='300px',width='600px',lbl='Zio')
        tc.contentPane(title='Miao')
        tc.contentPane(title='Bau')


    def test_2_tabindex(self, pane):
        "Use of tabindex to customize behaviour if you press tab. Label positioned on top"
        fb = pane.formbuilder(cols=2, lblpos='T')
        fb.textbox(value='^.val_1',lbl='Val 1',tabindex=1)
        fb.textbox(value='^.val_3',lbl='Val 3',tabindex=3)
        fb.textbox(value='^.val_2',lbl='Val 2',tabindex=2)
        fb.textbox(value='^.val_4',lbl='Val 4',tabindex=4)

    def test_3_tabindex(self, pane):
        "Use of byColumn, move vertically if you press tab. Last field is disabled"
        fb = pane.formbuilder(cols=4,byColumn=True, fld_width='100%')
        fb.textbox(value='^.val_1',lbl='Val 1')
        fb.textbox(value='^.val_3',lbl='Val 3')
        fb.textbox(value='^.val_2',lbl='Val 2')
        fb.textbox(value='^.val_4',lbl='Val 4')
        fb.textbox(value='^.val_5',lbl='Val 5')
        fb.textbox(value='^.val_7',lbl='Val 7')
        fb.textbox(value='^.val_6',lbl='Val 6')
        fb.textbox(value='^.val_8',lbl='Val 8', disabled=True)

    def test_4_widgets(self,pane):
        "Here you can see many widgets in action. By pressing shift you will see a tip on mouseover"
        weekdays='1:Monday,2:Tuesday,3:Wednesday,4:Thursday,5:Friday,6:Saturday,7:Sunday'
        colors='DeepSkyBlue,Fuchsia,Coral,Crimson,GoldenRod,Gray,Navy,Maroon,Teal'

        fb = pane.formbuilder(cols=2,lbl_font_weight='bold', lbl_color='^.lblcolor',
                                                 fld_width='100%', colswidth='auto',
                                                 margin='5px', datapath='widgets')
        
        fb.textBox(value='^.name',lbl='Name',placeholder='John', tooltip="This is a textBox")

        fb.numberTextBox('^.age',lbl='Age', placeholder='33',
                     tooltip="This is a NumberTextBox")
        
        fb.numberTextBox('^.weight',lbl='Weight', format='#.00',
                     tooltip="Weight Kg.")
            
        fb.dateTextBox('^.birthday',lbl='Birthday',
                     tooltip="This is a DateTextBox and you can click on icon")
        
        fb.checkBox('^.specialstuff',label='Special',
                                   tooltip="This is a checkBox")
                
        fb.filteringSelect('^.dayofweek',lbl='Day of week', 
                       tooltip="""FilteringSelect: you can select only an existing value.<br/>
                                  You see the description but in the store we will have the value.""",
                       values=weekdays)
        fb.radioButtonText('^.dayofweek',values=weekdays,
                        lbl='One Day',colspan=2,cols=4,
                        tooltip="""radioButtonText.Select your preferred day.""")

        fb.checkBoxText('^.preferred_days',values=weekdays,
                        lbl='Preferred days',colspan=2,
                        cols=4,
                    tooltip="""CheckBoxText.Select your preferred days.""")

        fb.checkBoxText('^.preferred_days',values=weekdays,cols=4,
                        lbl='Preferred days',popup=True,colspan=2,
                        tooltip="""CheckBoxText.Select your preferred days in popup or type them.""")
    
        fb.comboBox('^.lblcolor',lbl='Labels Color', default_value='Gray',
                    values=colors,
                    tooltip="""This is a comboBox. <br/>
                               Select a default color for labels or type a new one.""" )
       
        fb.horizontalSlider('^.rounded',lbl='Rounded',minimum=0,maximum=59,
                               discreteValues=60,width='160px',
                             intermediateChanges=True,
                                tooltip="""HorizontaSlider.Change the box rounded border radius.""")
        
        fb.button('Submit',action="alert(data.toXml())",
                  tooltip="""Button.Click to get the xml of the data.""",
                  data='=widgets')
    
    def test_5_nested(self, pane):
        "Nested formbuilders"
        fb = pane.formbuilder(cols=2, lblpos='T')
        fb.textbox(value='^.val_1',lbl='Val 1')
        fb.textbox(value='^.val_3',lbl='Val 3')
        nested_fb = fb.formbuilder(cols=1, lblpos='L')
        nested_fb.textbox(value='^.val_2',lbl='Val 2')
        nested_fb.textbox(value='^.val_4',lbl='Val 4')
        nested_fb2 = fb.formbuilder(cols=1, lblpos='L')
        nested_fb2.textbox(value='^.val_5',lbl='Val 5')
        nested_fb2.textbox(value='^.val_6',lbl='Val 6')

    def test_6_field(self, pane):
        "You can specify table as fb attribute. This way you can use field widget"
        fb = pane.formbuilder(cols=2, table='glbl.provincia')
        fb.field('sigla')
        fb.field('regione')
        fb.field('nome')
        fb.field('codice')
        fb.field('codice_istat')

