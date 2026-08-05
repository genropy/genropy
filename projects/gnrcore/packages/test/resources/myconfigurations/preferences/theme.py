# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Theme', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.checkbox(value='^.dark_mode', label='Dark mode')
        fb.filteringSelect(value='^.font_size', lbl='Font size',
                           values='small:Small,medium:Medium,large:Large')
