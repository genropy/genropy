# -*- coding: utf-8 -*-

"Checkbox e checkboxtext"

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

    def test_10_mask_icon_colors(self, pane):
        "Checkbox and radio icons adapt to text color via CSS mask-image + currentColor"
        fb = pane.formbuilder(cols=1, border_spacing='6px')

        fb.div('Default context (inherits page text color)', font_weight='bold')
        fb.checkbox(value='^.c1', label='Default checkbox')
        fb.radioButtonText(values='a:Alpha,b:Beta,c:Gamma', value='^.r1')

        fb.div('Dark background, white text', font_weight='bold', margin_top='10px')
        dark = fb.div(background='#1E3055', color='white', padding='10px',
                      border_radius='8px')
        darkfb = dark.formbuilder(cols=1, border_spacing='4px')
        darkfb.checkbox(value='^.c2', label='White checkbox')
        darkfb.radioButtonText(values='x:One,y:Two,z:Three', value='^.r2')
        darkfb.checkBoxText(values='A:Apple,B:Banana,C:Cherry', value='^.c2t')

        fb.div('Red text context', font_weight='bold', margin_top='10px')
        red = fb.div(color='#cc0000', padding='10px')
        redfb = red.formbuilder(cols=1, border_spacing='4px')
        redfb.checkbox(value='^.c3', label='Red checkbox')
        redfb.radioButtonText(values='p:Pizza,q:Pasta,r:Risotto', value='^.r3')

        fb.div('Green text context', font_weight='bold', margin_top='10px')
        green = fb.div(color='#006600', padding='10px')
        greenfb = green.formbuilder(cols=1, border_spacing='4px')
        greenfb.checkbox(value='^.c4', label='Green checkbox')
        greenfb.checkBoxText(values='1:One,2:Two,3:Three', value='^.c4t')

        fb.div('Icon classes (checkboxOn/Off, radioOn/Off)', font_weight='bold', margin_top='10px')
        icons = fb.div(padding='10px')
        iconsfb = icons.formbuilder(cols=4, border_spacing='6px')
        iconsfb.div(_class='checkboxOn', width='1.4em', height='1.4em', lbl='checkboxOn')
        iconsfb.div(_class='checkboxOff', width='1.4em', height='1.4em', lbl='checkboxOff')
        iconsfb.div(_class='radioOn', width='1.4em', height='1.4em', lbl='radioOn')
        iconsfb.div(_class='radioOff', width='1.4em', height='1.4em', lbl='radioOff')

        fb.div('Icon classes in blue context', font_weight='bold', margin_top='10px')
        blue = fb.div(color='#0055cc', padding='10px')
        bluefb = blue.formbuilder(cols=4, border_spacing='6px')
        bluefb.div(_class='checkboxOn', width='1.4em', height='1.4em', lbl='checkboxOn')
        bluefb.div(_class='checkboxOff', width='1.4em', height='1.4em', lbl='checkboxOff')
        bluefb.div(_class='radioOn', width='1.4em', height='1.4em', lbl='radioOn')
        bluefb.div(_class='radioOff', width='1.4em', height='1.4em', lbl='radioOff')
