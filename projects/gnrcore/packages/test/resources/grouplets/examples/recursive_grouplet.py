# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Recursive Grouplet', priority=2)

    def grouplet_main(self, pane, **kwargs):
        tc = pane.tabContainer(height='300px', width='400px',margin_top='5px',margin_left='5px')
        data_tab = tc.contentPane(title='Data')
        fb = data_tab.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.field1', lbl='Field 1')
        fb.textbox(value='^.field2', lbl='Field 2')
        nested_tab = tc.contentPane(title='Nested')
        nested_tab.grouplet(value='^.nested', resource='examples/recursive_grouplet')
