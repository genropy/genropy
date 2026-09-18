# -*- coding: utf-8 -*-

"""First step of the red wizard probe: an empty pane painted red.

Debug probe for the center-chain sizing: the red area shows exactly the
box the framework gives the step content. It must fill the wizard center
at every dialog size."""

from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Tipo', priority=1)

    def grouplet_main(self, pane, **kwargs):
        pane.attributes.update(background='red')
        return
