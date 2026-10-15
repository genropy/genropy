# -*- coding: utf-8 -*-

"""Struct objects passed to javascript as attributes

A node built in Python can be handed to another node as an ordinary keyword
attribute: in the javascript of that node the name resolves to the source
node, so an action reaches another widget without a `nodeId` to look it up.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_a(self, pane):
        """The button reads the widget of a textbox passed to it as `tb1`; the fields write absolute paths

        `aaa`, `bbb` and `ccc` have no leading dot on purpose: they live at the
        root of the page data, an external store shared by the whole page and
        not under this case.
        """
        fb = pane.formbuilder(cols=1)
        tb1 = fb.textbox(value='^aaa', lbl='aaa')
        fb.textbox(value='^bbb', lbl='bbb')
        fb.div('^ccc')
        pane.dataFormula('ccc', 'a+" - "+b', a='^aaa', b='^bbb')
        pane.button(label='Read widget', action="SET .widget_class = tb1.widget.declaredClass;", tb1=tb1)
        pane.div('^.widget_class')

    def test_2_b(self, pane):
        """Publishing to a node through its struct object: the handler receives the button passed as `btn`"""
        xxx = pane.button(label='ttt')
        box = pane.div(height='12px', width='12px', background='red',
                       selfsubscribe_test="this.setRelativeData('.received', btn.attr.label);",
                       btn=xxx)
        pane.button('test 2', action='box.publish("test")', box=box)
        pane.div('^.received')

    def test_3_c(self, pane):
        """Two buttons publish the same topic to two different boxes, each answering with its own width"""
        box = pane.div(height='20px', width='500px',
                       selfsubscribe_dimmi_larghezza='this.domNode.innerHTML=this.attr.width;', background='white')
        box2 = pane.div(height='20px', width='300px',
                        selfsubscribe_dimmi_larghezza='this.domNode.innerHTML= this.attr.width;', background='green')
        pane.button('Width of A', action='box.publish("dimmi_larghezza");', box=box)
        pane.button('Width of B', action='box.publish("dimmi_larghezza");', box=box2)
