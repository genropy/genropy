# -*- coding: utf-8 -*-

class Grouplet(object):
    def __info__(self):
        return dict(caption='Legacy Preference Bridge', priority=999)

    def grouplet_main(self, pane, locationpath=None, **kwargs):
        if not locationpath:
            return
        panecb = getattr(self, f'prefpane_{locationpath}', None)
        if panecb:
            panecb(pane, nodeId=locationpath, _anchor=True)
