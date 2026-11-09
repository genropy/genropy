# -*- coding: utf-8 -*-

"""Attaching a menu or a tooltipPane to a textbox

A textbox is `position='relative'` here so that comboMenu, comboArrow and
tooltipPane can be anchored to it: the menu and the pane are children of the
textbox, not siblings placed by hand. The last case is textboxMenu, the ready
widget for a textbox holding several values joined by a separator.
"""


class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    dojo_source=True
    
    def windowTitle(self):
        return 'ComboArrow'
         
    def test_1_Menu(self,pane):
        """comboMenu: a fixed list of values dropping down from the textbox"""
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.val', lbl='Choose Value',position='relative').comboMenu(values='Pippo,Pluto,Paperino',_class='smallmenu')
    
    def test_1_Tooltip(self,pane):
        """comboArrow plus tooltipPane: the arrow opens a pane holding arbitrary content"""
        fb = pane.formbuilder(cols=2)
        tooltip = fb.textbox(value='^.val', lbl='Choose Value',position='relative').comboArrow().tooltipPane()
        tooltip.div('Ciao come va?',height='100px',width='200px')

    
    def test_2_tooltipTextArea(self,pane):
        """The same pane holding a textarea bound to the textbox value, so both edit it"""
        fb = pane.formbuilder(cols=2)
        tooltip = fb.textbox(value='^.val', lbl='Choose Value',position='relative').comboArrow().tooltipPane()
        tooltip.simpleTextArea(value='^.val',height='100px',width='200px')


    def test_3_tooltipTextArea(self,pane):
        """multilineTextbox: the previous case as one widget, no pane to wire"""
        fb = pane.formbuilder(cols=2)
        fb.multilineTextbox(value='^.test', lbl='Multiline content')

    def test_4_TextBoxMenu(self,pane):
        """textboxMenu: the chosen values accumulate in the textbox, joined by the separator"""
        fb = pane.formbuilder(cols=2)
        fb.textboxMenu(value='^.val', lbl='Choose Value',separator='|',position='relative',values='Pippo,Pluto,Paperino')
