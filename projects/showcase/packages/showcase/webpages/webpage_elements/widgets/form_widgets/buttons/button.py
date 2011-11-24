# -*- coding: UTF-8 -*-
"""Buttons"""

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_action(self,pane):
        """Action attribute"""
        fb = pane.formbuilder(cols=3)
        fb.div('The action attribute allow to write javascript code', colspan=3)
        fb.button('alert', action="alert('Hello!')", tooltip='click me!', colspan=2)
        fb.div('Create an alert message through "action" attribute. There is a tooltip, too',
                font_size='.9em', text_align='justify')
        fb.button('confirm', action='confirm("Sure?")', colspan=2)
        fb.div('Create a confirm message through \"action\" attribute', font_size='.9em', text_align='justify')
        fb.button('Show screen resolution', showLabel=False,
                   action="SET .res = screen.width+' x '+screen.height;", iconClass='iconbox spanner')
        fb.textbox(value='^.res', width='6em')
        fb.div('Evaluate your screen resolution', font_size='.9em', text_align='justify')
        
    def test_2_graphical_attributes(self,pane):
        """Graphical attributes"""
        bc = pane.borderContainer()
        bc.data('.icon','icnBaseOk')
        bc.button('Click me',iconClass='^.icon', width='7.5em', background_color='green',
                   font_size='22px', font_family='Courier',
                   rounded=5, border='2px solid gray',
                   action="alert('Clicked!')")
                   
    def test_3_fire(self,pane):
        """macro (FIRE)"""
        bc = pane.borderContainer()
        bc.div("""There are three way to use FIRE:""",
                font_size='.9em',text_align='justify')
        bc.dataController('''alert(msg);''', msg='^.msg')
        fb = bc.formbuilder(cols=2)
        
        fb.button('Click me!',action="FIRE .msg='Click';")
        fb.div(""" "action="FIRE msg='Click';" [shows an alert message reporting "Click"] """,font_size='.9em')
        
        fb.button('Click me!',fire_Click = '.msg')
        fb.div(""" "fire_Click = 'msg'" [same result of the previous one]""",font_size='.9em')
        
        fb.button('Click me!',fire='.msg')
        fb.div(""" "fire='msg'" [shows an alert message reporting "true"] """,font_size='.9em')
        
    def test_4_set(self,pane):
        """macro (SET)"""
        pane.data('.number', 0)
        pane.dataController("""SET .number=36;""",_fired='^.my_button')
        bc = pane.borderContainer()
        fb = bc.formbuilder(cols=2)
        fb.div("""We gave the value 0 through a data controller. The button
                  contains a trigger for a dataController that has a \"SET\" macro
                  that give \"36\" every time it is clicked""",
                  font_size='.9em', text_align='justify', colspan=2)
        fb.button('36',fire='^.my_button')
        fb.numberSpinner(lbl='number', value='^.number')
        
        fb.div("""This time the button contains directly the \"SET\" macro""",
                  font_size='.9em', text_align='justify', colspan=2)
        fb.button('36', action='SET .number2=36;')
        fb.numberSpinner(lbl='number 2', value='^.number2')
        