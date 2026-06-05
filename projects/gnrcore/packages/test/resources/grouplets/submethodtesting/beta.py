# -*- coding: utf-8 -*-


class Grouplet(object):
    def __info__(self):
        return dict(caption='Beta', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        self.mainInfo(fb)

    def mainInfo(self, fb):
        fb.div('Built by beta', font_weight='bold', color='blue')
