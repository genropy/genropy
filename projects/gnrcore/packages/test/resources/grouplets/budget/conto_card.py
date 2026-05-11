"""Account ("conto") card grouplet — header + nested details grid.

Header: codice badge + editable description.
Body: nested groupletGrid of `dettaglio_row` with a sticky column header
row in the top slot. Columns stay pixel-aligned because the header
reuses the same `gg-dettagli-grid` template as the row body. Shared
dragCode ('budget_dettagli') so details can be moved across accounts.
Add a detail via the default phantom add-cell at the bottom; delete via
the per-row kebab.
"""
from gnr.web.gnrbaseclasses import BaseComponent


COLUMNS = [
    ('Tipo', 'gg-dett-tipo'),
    ('Descrizione', 'gg-dett-descr'),
    ('Fase', 'gg-dett-fase'),
    ('Data rif.', 'gg-dett-data'),
    ('N.Ris', 'gg-dett-num'),
    ('Qt', 'gg-dett-num'),
    ('P.U.', 'gg-dett-prezzo'),
    ('IVA', 'gg-dett-iva'),
    ('Al.Oneri', 'gg-dett-iva'),
    ('Al.Rit.', 'gg-dett-iva'),
    ('Distribuz.', 'gg-dett-distrib'),
    ('Tot.Netto', 'gg-dett-tot'),
]


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
        body = card.div(_class='gg-conto-body')
        grid = body.groupletGrid(
            storepath='.details',
            resource='budget/dettaglio_row',
            _class='gg-dettagli-host',
            dragCode='budget_dettagli',
            defaultRow=dict(tipo='ACQ', descrizione='',
                            qty=1, p_u=0, iva=22))
        header = grid.top.div(
            _class='gg-dettagli-grid gg-dettagli-header')
        for label, css in COLUMNS:
            header.div(label, _class=css)
