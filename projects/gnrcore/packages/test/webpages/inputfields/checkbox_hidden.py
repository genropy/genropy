# -*- coding: utf-8 -*-

"""Checkbox hidden/visibility scenarios"""

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_hidden_binding(self, pane):
        "Checkbox hidden bound to another field value"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        fb.textbox(value='^.name', lbl='Name')
        fb.checkbox(value='^.confirm', label='Confirm',
                    lbl='Confirm', hidden='^.name?=!#v')
        fb.div('^.confirm', lbl='Value')

    def test_1_hidden_binding_toggle(self, pane):
        "Toggle checkbox hidden bound to another field value"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        fb.textbox(value='^.name', lbl='Name')
        fb.checkbox(value='^.accept', label='Accept terms',
                    lbl='Accept', toggle=True,
                    hidden='^.name?=!#v')
        fb.div('^.accept', lbl='Value')

    def test_2_hidden_static_false(self, pane):
        "Checkbox with hidden=False (always visible)"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        fb.checkbox(value='^.always_visible', label='Always visible',
                    lbl='Visible', hidden=False)

    def test_3_hidden_controller(self, pane):
        "Checkbox hidden controlled by another checkbox"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        fb.checkbox(value='^.show_extra', label='Show extra options')
        fb.checkbox(value='^.option_a', label='Option A',
                    lbl='Extra A', hidden='^.show_extra?=!#v')
        fb.checkbox(value='^.option_b', label='Option B',
                    lbl='Extra B', hidden='^.show_extra?=!#v')
        fb.div('^.option_a', lbl='A value')
        fb.div('^.option_b', lbl='B value')

    def test_4_ask_with_checkbox(self, pane):
        "Checkbox in _ask dialog with conditional visibility"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        btn = fb.button('Open ask dialog')
        btn.dataRpc('.result', self.askResult,
                    _ask=dict(title='Test ask with checkbox',
                              fields=[
                                  dict(name='reason', tag='textbox', lbl='Reason'),
                                  dict(name='confirm', tag='checkbox', lbl='Confirm',
                                       hidden="^.reason?=!#v")
                              ]))
        fb.div('^.result', lbl='Result')

    @public_method
    def askResult(self, reason=None, confirm=None):
        return 'reason=%s, confirm=%s' % (reason, confirm)

    def test_5_ask_checkbox_no_hidden(self, pane):
        "Checkbox in _ask dialog without hidden (always visible)"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        btn = fb.button('Open ask dialog')
        btn.dataRpc('.result2', self.askResult2,
                    _ask=dict(title='Test ask checkbox always visible',
                              fields=[
                                  dict(name='note', tag='textbox', lbl='Note'),
                                  dict(name='flag', tag='checkbox', lbl='Flag')
                              ]))
        fb.div('^.result2', lbl='Result')

    @public_method
    def askResult2(self, note=None, flag=None):
        return 'note=%s, flag=%s' % (note, flag)

    def test_6_multiple_toggle_cycles(self, pane):
        "Rapidly toggle visibility multiple times"
        fb = pane.formbuilder(cols=1, border_spacing='6px')
        fb.checkbox(value='^.toggle_switch', label='Toggle visibility')
        fb.checkbox(value='^.target_cb', label='I appear and disappear',
                    lbl='Target', hidden='^.toggle_switch?=!#v')
        fb.div('Toggle the switch multiple times, the checkbox should always render correctly')

    def test_7_hidden_in_multicol_fb(self, pane):
        "Checkbox hidden in a multi-column formbuilder"
        fb = pane.formbuilder(cols=2, border_spacing='6px')
        fb.textbox(value='^.first', lbl='First')
        fb.textbox(value='^.second', lbl='Second')
        fb.checkbox(value='^.cb1', label='Check 1',
                    lbl='Check 1', hidden='^.first?=!#v')
        fb.checkbox(value='^.cb2', label='Check 2',
                    lbl='Check 2', hidden='^.second?=!#v')
