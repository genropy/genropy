# -*- coding: utf-8 -*-

info = dict(caption='Alfa', code='alfa', priority=1)


class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        self.mainInfo(fb)

    def mainInfo(self, fb):
        fb.div('Built by alfa', font_weight='bold', color='green')
