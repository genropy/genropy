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

