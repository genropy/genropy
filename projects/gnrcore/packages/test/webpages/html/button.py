# -*- coding: utf-8 -*-

"Test Button"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def test_0_simplebutton(self,pane):
        "Simple button alert: insert text and launch alert"
        pane.textbox('^.message',lbl='Message')
        pane.button('Launch', action="""alert(message); 
                                        console.log("you clicked me ",event,_counter)""", 
                                _delay=50, message='=.message')

    def test_1_styled(self, pane):
        "Simple button alert but styled: insert text and launch alert"
        pane.button('Click me',
                     action="""var sure = confirm("Format your PC/Mac?");
                               if (sure == true){alert("formatted!")};""",
                     style='color:red;font-size:44px;')

    def test_2_buttonSet(self,pane):
        """Copy value into other field"""
        fb = pane.formbuilder()
        fb.textbox('^.sorgente',lbl='Sorgente')
        fb.button('Copia',action='SET .destinazione = v;',
                    v='=.sorgente')
        fb.textbox('^.destinazione',lbl='Destinazione')

    def test_3_buttonAsk(self,pane):
        "Button with ask: press button and insert fields into dialog"
        pane.button('Set value',
                    action="""SET .myvalue = myvalue;
                              SET .mycolor = mycolor;""",
                        ask=dict(title='Which one',
                                fields=[dict(name='myvalue',lbl='My value',
                                            validate_notnull=True),
                                        dict(name='mycolor',lbl='Color',
                                                tag='combobox',
                                                values='orange,green,blue')])
                                )
        pane.div('^.myvalue',color='^.mycolor')
        
    def test_4_shortcut(self, pane):
        """Just messing with buttons... Try using shortcuts (F1, F2) inside and outside dialog"""
        tc = pane.contentPane(height='150px',width='400px')
        tc.button('Quit', action='alert("Quit")',_shortcut='f1',nodeId='qtbtn')
        tc.button('Quot', action='alert("Quot")',_shortcut='f2',disabled='^.disabled_quot')
        tc.checkbox(value='^.disabled_quot',label='Disabled quot',default=True)
        box = tc.div(border='1px solid silver',margin='4px',padding='10px')
        tc.button('Create buttons',action="""
            var cb = function(){
                console.log(arguments);
            }
            box._('button',{action:cb,label:'Dynamic',_shortcut:'f2'});
            box._('button',{action:cb,label:'Dynamic 2',_shortcut:'f2',nodeId:'number2'});
            box._('button',{action:'genro.nodeById("number2")._destroy()',label:'kill 2'});
        """,box=box)

        dlg = tc.dialog(title='Hello',height='300px',width='400px',closable=True)
        tc.button('Open dialog', action='dlg.show()',dlg=dlg.js_widget)
        tc.button('Shortcut', action='alert("underdialog")',_shortcut='f2')
        dlg.button('Inside dialog', action='alert("Inside dialog")',_shortcut='f2')

    def test_5_slotButton(self, pane):
        """slotButton vs standard button"""
        fb = pane.formbuilder(cols=3)
        fb.slotButton('I\'m the label, but I work as a tooltip', iconClass="icnBuilding", action='alert("Hello!")',colspan=2)
        fb.div('This is the standard usage of a slotButton: the label works as a tooltip')
        fb.button('button + icon', iconClass="icnBuilding",
                   action='alert("fb.button(\'button + icon\', iconClass=\'icnBuilding\')")')
        fb.slotButton('slotButton + icon', showLabel=True, iconClass="icnBuilding",
                       action='alert("fb.slotButton(\'slotButton + icon\', showLabel=True, iconClass=\'icnBuilding\')")')
        fb.div('Here we have a button and a slotButton set equal (with the "iconClass" attribute)')
        fb.button('button', action='alert("fb.button(\'button\')")')
        fb.slotButton('slotButton', action='alert("fb.slotButton(\'slotButton\')")')
        fb.div('Here we have a button and a slotButton set equal (without the "iconclass" attribute)')

    def test_6_lightbutton(self, pane):
        "Lightbutton: different lighter style"
        pane.lightbutton("Even if you don't think so, I am a button", action='alert(msg)', msg='=msg',
                        ask=dict(title='Test',fields=[dict(name='msg',lbl='Message')]))

    def test_7_lightbutton_controller(self, pane):
        """Use of lightbutton (no style) to attach dataController
        Lightbutton differs in style from normal button, but it works in the same way.
        Here we attach a dataController directly to the button"""
        btn = pane.lightbutton('What time is it?')
        btn.dataController('var now = new Date().toISOString(); SET .time=now;')
        pane.div('^.time')
