# -*- coding: utf-8 -*-

info = dict(caption='Recursive Grouplet', code='recursive_grouplet', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        tc = pane.tabContainer(height='300px', width='400px')
        data_tab = tc.contentPane(title='Data')
        fb = data_tab.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.field1', lbl='Field 1')
        fb.textbox(value='^.field2', lbl='Field 2')
        nested_tab = tc.contentPane(title='Nested')
        nested_tab.grouplet(value='^.nested', resource='recursive_grouplet')
