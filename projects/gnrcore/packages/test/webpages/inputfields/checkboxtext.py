# -*- coding: utf-8 -*-

"Checkbox e checkboxtext"

from logging import PlaceHolder


class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"
         
    def test_0_mode_values(self,pane):
        "Use attr 'values' to define which values to show and store (values will be separated by comma)"
        pane.checkBoxText(value='^.pluto',values='Foo,Bar,/,Span,Mol,Tol,Rol,Cor,Sar',
                    table_border_spacing='10px',label_color='red',cols=3)
        pane.textbox(value='^.pluto')
    
    def test_1_mode_codes(self,pane):
        "It's possible to store a different value (e.g. codes), using ':'."
        pane.radioButtonText(values='foo:Foo,bar:Bar,span:Span',value='^.pluto',group='test')
        pane.textbox(value='^.pluto', lbl='value')
        pane.textbox(value='^.pluto?_displayedValue', lbl='_displayedValue')

    def test_2_multicbpopup(self,pane):
        "Use checkbox to disable fields. Possibility to show values in a popup."
        pane.checkbox(value='^.disabled',label='disabled')
        pane.checkBoxText(values="""0:Lunedì\\2,1:Mar,2:Mer,3:Gio,4:Ven,5:Sab,6:Dom""",
        value='^.pluto',cols=3,popup=True,disabled='^.disabled',readOnly=True)
                            
    def test_3_multicb(self,pane):
        "It's possible to separate columns manually using '/'"
        pane.checkBoxText(values="""0:Foo,1:Bar,/,3:Span,4:Zum,5:Pap,6:Mas,/,8:Ilo""",value='^.pluto')

    def test_4_mode_values(self,pane):
        "Same as before but with radiobutton, which is mutually exclusive"
        pane.data('.values','M:Maschio,F:Femmina')
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.radioButtonText(values='^.values',value='^.pluto')
        fb.textbox(value='^.pluto',lbl='code')
        fb.textbox(value='^.pluto?_displayedValue',lbl='Caption')
        fb.textbox(value='^.values',lbl='Values')   
   
    def test_5_mode_table(self,pane):
        "Checkboxtext can be used in every struct cell with 'tag='checkBoxText'"
        bc = pane.borderContainer(height='400px')
        def struct(struct):
            r = struct.view().rows()
            r.cell('users_pkeys',name='users',edit=dict(tag='checkBoxText',table='adm.user'),width='40em',caption_field='users')

        bc.contentPane(region='center').bagGrid(storepath='main.test',struct=struct)

    def test_6_testhatag(self,pane):
        "Values can be set using a button and displayed"
        pane.button('TEST',action='SET .tag="admin,manager";')
        pane.checkBoxText(value='^.tag',table='adm.htag',popup=True,hierarchical=True,alt_pkey_field='code',
                            labelAttribute='code')

    def test_7_localization(self,pane):
        "Use !![en] to display values in different languages"
        pane.checkBoxText(values="fatt:[!![it]Fattura],cli:[!![it]Cliente]",value='^.cbt',popup=True)
        pane.filteringSelect(values="fatt:[!![it]Fattura],cli:[!![it]Cliente]",value='^.flt')
        pane.multiButton(values="fatt:[!![it]Fattura],cli:[!![it]Cliente]",value='^.mb')

    def test_8_mode_valuesCb(self,pane):
        "Build values using 'valuesCb'"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.source',lbl='Source for cb', default='F:Foo,B:Bar,S:Span')
        fb.checkBoxText(value='^.currval',
                        valuesCb="""var result = [];
                            source = this.getRelativeData('.source');
                            source = source?source.split(','):['Foo','Bar','Span'];
                            source.forEach(function(n,idx){
                                var code = 'val_'+idx;
                                result.push(code+':'+n);
                            });
                            return result.join(',');
                        """,lbl='Checkbox dynamic')
        fb.textbox(value='^.currval',lbl='val')
        fb.textbox(value='^.currval?_displayedValue',lbl='val caption')

    def test_9_toggle(self, pane):
        "Use toggle attribute to display checkbox with a toggle icon"
        pane.checkbox(value='^.enabled',label='Enabled', toggle=True)