# -*- coding: utf-8 -*-

# slotbar.py
# Created by Francesco Porcari on 2011-01-30.
# Copyright (c) 2011 Softwell. All rights reserved.

"""slotBar and slotToolbar: a bar whose content is declared as a list of named slots

The `slots` string is the whole interface of the widget: every name in it becomes
a child the page fills afterwards (`bar.foo.div(...)`), `*` is elastic space, `|`
a separator and a bare number a fixed-width gap. `slotToolbar` is the toolbar
flavour of the same bar and both go on any region of a framePane, horizontal on
top, stacked on left. A slot can also be a `struct_method` reused by many bars,
as `myslot` is here, and the whole set can be rewritten after the fact with
`replaceSlots`.
"""


from gnr.web.gnrwebstruct import struct_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'SlotBar test'

    def test_0_slotbar_base(self,pane):
        """Basic slotbar: named slots, fixed-width spacers, separators and a custom slot"""
        frame = pane.framePane(frameCode='frameOne',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        top = frame.top.slotBar(slots='30,foo,|,Antonio,*,|,bar',height='20px')
        top.foo.div('foo',width='100px',background='navy',lbl='Foo')
        top.bar.myslot()

    def test_1_slotbar(self,pane):
        """CSS on slotbar: gradient, rounded corners and the slot label styled through lbl_*"""
        frame = pane.framePane(frameCode='frameOneCss',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        top = frame.top.slotBar(slots='*,|,foo,bar,|,*',
                                gradient_deg=90,gradient_from='#fff',gradient_to='#bbb',
                                border_bottom='1px solid #bbb',rounded_top=10,lbl_position='T',lbl_color='red',
                                lbl_font_size='7px')
        top.foo.div('foo',width='100px',background='navy',lbl='Foo')
        top.bar.myslot()

    def test_2_slotToolbar(self,pane):
        """CSS on slotToolbar: the same styling on the toolbar flavour of the bar"""
        frame = pane.framePane(frameCode='frameTwo',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        top = frame.top.slotToolbar(slots='*,|,foo,bar,|,*,xx',
                                    gradient_deg='90',gradient_from='#fff',gradient_to='#bbb',
                                    border_bottom='1px solid #bbb',rounded_top=10,
                                    lbl_position='T',lbl_color='red',lbl_font_size='7px')
        top.foo.div('foo',width='100px',color='white',background='teal',lbl='labelFoo')
        top.bar.myslot()
        top.xx.div(width='1px')

    def test_3_slotToolbar_vertical(self,pane):
        """slotToolbar on the left region, so the slots stack vertically"""
        frame = pane.framePane(frameCode='frameTwoVertical',height='300px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_left=10,margin='10px')
        sl = frame.left.slotToolbar(slots='10,foo,*,|,bar,|,*,spam,*',
                                    border_right='1px solid gray',
                                    gradient_from='#bbb',gradient_to='#fff',
                                    rounded_left=10,toolbar=True)
        sl.foo.button(label='Add',iconClass='icnBaseAdd',showLabel=False)
        sl.bar.button(label='Del',iconClass='icnBaseOk',showLabel=False)
        sl.spam.div(height='18px',width='16px',background='blue')

    def test_4_slotToolbar_replaceslots(self,pane):
        """replaceSlots swaps a declared slot for another one after the bar is built"""
        frame = pane.framePane(height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')
        bar = frame.top.slotBar('aaa,bbb',aaa='Piero',bbb='Pippo')
        bar.replaceSlots('bbb','ccc',ccc='Pancrazio')

    @struct_method
    def myslot(self,pane):
        """Custom slot shared by the first three cases: an icon-only button with a label"""
        pane.button(label='Bar',iconClass='icnBaseAdd',showLabel=False,lbl='hello')

    def test_5_slotToolbar_multiline(self,pane):
        """Two slotToolbars stacked on the same top region, the upper one carrying a multibutton"""
        frame = pane.framePane(frameCode='frameMultiline',height='100px',shadow='3px 3px 5px gray',
                                border='1px solid #bbb',rounded_top=10,margin='10px')

        upperbar = frame.top.slotToolbar(slots='*,tagpicker,*',
                                    gradient_deg='90',gradient_from='#fff',gradient_to='lime',
                                    border_bottom='1px solid #bbb',
                                    lbl_position='T',lbl_color='red',lbl_font_size='7px',childname='topupper')
        upperbar.tagpicker.multibutton(values='^.multibutton_values',value='^.picked_tags',multivalue=True,mandatory=False)
        upperbar.dataController('SET .multibutton_values = v',v ='^.valuesetter')

        top = frame.top.slotToolbar(slots='*,|,foo,bar,|,*,xx',
                                    gradient_deg='90',gradient_from='#fff',gradient_to='#bbb',
                                    border_bottom='1px solid #bbb',splitter=True,
                                    lbl_position='T',lbl_color='red',lbl_font_size='7px')

        top.foo.div('foo',width='100px',color='white',background='teal',lbl='labelFoo')
        top.bar.myslot()
        top.xx.div(width='1px')
        frame.textbox(value='^.valuesetter')
        frame.dataFormula('.valuesetter','v',v = 'pippo:mmaa:Pippo,pluto:Pluto,paperino:Paperino',_onStart=True)

        center = frame.center.contentPane()
        center.textbox(value='^.picked_tags')
