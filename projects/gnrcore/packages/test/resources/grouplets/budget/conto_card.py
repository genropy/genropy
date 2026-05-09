"""Account ("conto") card grouplet — Step 1: header only.

Header: codice + editable description. No nested details grid yet —
Step 2 will add it.
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Budget Account Card', priority=11)

    def grouplet_main(self, pane, **kwargs):
        card = pane.div(_class='gg-conto-card')
        head = card.div(_class='gg-conto-head')
        head.div('^.codice', _class='gg-conto-codice')
        head.textbox(
            value='^.descr',
            placeholder='!!Account description',
            _class='gg-conto-descr',
            lbl=None)
