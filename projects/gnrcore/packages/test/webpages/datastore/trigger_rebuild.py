# -*- coding: utf-8 -*-

"""Data node subscriptions across subtree rebuilds (#1206)"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_datacontroller_survives_rebuild(self, pane):
        """Type in Input: Fired increments by 1 every time, Formula doubles it.
        Click Rebuild box (even many times), then type again: both must still react."""
        fb = pane.formbuilder(cols=4, border_spacing='3px')
        fb.textbox(value='^.input', lbl='Input')
        fb.button('Rebuild box').dataController("genro.nodeById('rb_box_0').rebuild();")
        fb.numberTextBox(value='^.counter', lbl='Fired', readOnly=True)
        fb.numberTextBox(value='^.doubled', lbl='Formula', readOnly=True)
        box = pane.contentPane(nodeId='rb_box_0', border='1px solid silver',
                               padding='5px', margin='5px')
        box.div('The dataController and dataFormula of this box must survive its rebuild')
        box.dataController("SET .counter = (GET .counter || 0) + 1;", _fired='^.input')
        box.dataFormula('.doubled', 'inp*2', inp='^.counter')

    def test_1_datacontroller_under_if(self, pane):
        """Type in Input: Fired increments. Uncheck and recheck Visible (the box
        rebuilds, like documentFrame does on every reload), then type again:
        Fired must keep incrementing."""
        pane.data('.flag', True)
        fb = pane.formbuilder(cols=3, border_spacing='3px')
        fb.textbox(value='^.input', lbl='Input')
        fb.checkbox(value='^.flag', label='Visible')
        fb.numberTextBox(value='^.counter', lbl='Fired', readOnly=True)
        box = pane.contentPane(_if='^.flag', border='1px solid silver',
                               padding='5px', margin='5px')
        box.div('Box governed by _if')
        box.dataController("SET .counter = (GET .counter || 0) + 1;", _fired='^.input')

    def test_2_remote_content_replaced(self, pane):
        """Change Reload token: the remote content is replaced with a fresh one.
        Then type in Probe: Fired must increment by EXACTLY 1 per keystroke
        (a higher step means stale subscriptions of the discarded content)."""
        fb = pane.formbuilder(cols=3, border_spacing='3px')
        fb.textbox(value='^.token', lbl='Reload token')
        fb.textbox(value='^.probe', lbl='Probe')
        fb.numberTextBox(value='^.counter', lbl='Fired', readOnly=True)
        pane.contentPane(border='1px solid silver', padding='5px',
                         margin='5px').remote(self.remoteInner, token='^.token')

    @public_method
    def remoteInner(self, pane, token=None, **kwargs):
        pane.div('Remote content for token: %s' % (token or ''))
        pane.dataController("SET .counter = (GET .counter || 0) + 1;", _fired='^.probe')

    def test_3_sibling_isolation(self, pane):
        """Rebuild box A many times, then type in both inputs: each counter
        increments by exactly 1 on its own input. Box B must never be affected
        by the rebuilds of box A."""
        fb = pane.formbuilder(cols=5, border_spacing='3px')
        fb.textbox(value='^.input_a', lbl='Input A')
        fb.textbox(value='^.input_b', lbl='Input B')
        fb.button('Rebuild A').dataController("genro.nodeById('rb_box_a').rebuild();")
        fb.numberTextBox(value='^.counter_a', lbl='Fired A', readOnly=True)
        fb.numberTextBox(value='^.counter_b', lbl='Fired B', readOnly=True)
        box_a = pane.contentPane(nodeId='rb_box_a', border='1px solid silver',
                                 padding='5px', margin='5px')
        box_a.div('Box A')
        box_a.dataController("SET .counter_a = (GET .counter_a || 0) + 1;", _fired='^.input_a')
        box_b = pane.contentPane(border='1px solid silver', padding='5px', margin='5px')
        box_b.div('Box B')
        box_b.dataController("SET .counter_b = (GET .counter_b || 0) + 1;", _fired='^.input_b')
