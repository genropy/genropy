"""Chapter ("capitolo") card grouplet — Step 1: header + accounts.

Header: codice badge + editable description.
Body: nested groupletGrid of `conto_card` with shared `dragCode`
('budget_conti') so accounts can be dragged across chapters.

No total yet — Step 3 will add the dataFormula cascade.
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Budget Chapter Card', priority=12)

    def grouplet_main(self, pane, **kwargs):
        card = pane.div(_class='gg-capitolo-card')
        head = card.div(_class='gg-capitolo-head')
        head.div('^.codice', _class='gg-capitolo-codice')
        head.textbox(
            value='^.descr',
            placeholder='!!Chapter description',
            _class='gg-capitolo-descr',
            lbl=None)
        body = card.div(_class='gg-capitolo-body')
        body.groupletGrid(
            storepath='.accounts',
            resource='budget/conto_card',
            addEnabled=True,
            removeEnabled=True,
            dragCode='budget_conti',
            defaultRow=dict(codice='', descr=''))
