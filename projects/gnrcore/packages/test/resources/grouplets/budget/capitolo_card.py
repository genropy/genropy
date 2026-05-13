"""Chapter ("capitolo") tab content — accounts + chapter total footer.

The enclosing groupletGrid renders chapters as tabs (`layout='tabs'`,
`titleField='descr'`), so the chapter description IS the tab chip and
this grouplet renders only the tab body: a nested groupletGrid of
`conto_card`, plus a small footer with the chapter total. Accounts
can be dragged across chapters via the shared
`dragCode='budget_conti'`.

Totals cascade:
  detail.tot_netto  → conto.tot_conto  → capitolo.tot_capitolo
                      (sum in conto)    (sum in capitolo)
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Budget Chapter Card', priority=12)

    def grouplet_main(self, pane, **kwargs):
        # Title as a borderless textbox at the top of the tab body
        # (same idiom as `kanban_card`). The tab chip mirrors `^.descr`
        # reactively via `titleField`, so editing here updates the chip.
        pane.textbox(value='^.descr',
                     placeholder='!!Chapter title',
                     lbl=None,
                     font_weight='700', font_size='18px',
                     border='none', background='transparent',
                     padding='4px 6px', margin_bottom='8px',
                     width='100%')
        pane.groupletGrid(
            storepath='.accounts',
            resource='budget/conto_card',
            dragCode='budget_conti',
            additem_class='grouplet_grid_footer--minimal',
            additem_label='!!Add account',
            counterField='codice',
            defaultRow=dict(codice='', descr=''))
        # Chapter total: sum `tot_conto` across all account rows. Each
        # conto_card publishes `.tot_conto` via its own dataFormula, so
        # this rolls up live as details deeper in the tree change.
        pane.dataFormula(
            '.tot_capitolo',
            'accounts ? accounts.sum("tot_conto") : 0',
            accounts='^.accounts')
        footer = pane.div(_class='gg-capitolo-footer')
        footer.div('Totale capitolo', _class='gg-capitolo-footer-label')
        footer.div('^.tot_capitolo?=genro.formatter.asText(#v, '
                   '{format: "#,##0.00"})',
                   _class='gg-capitolo-footer-value')
