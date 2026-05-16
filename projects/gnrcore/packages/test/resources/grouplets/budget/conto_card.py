"""Account ("conto") row — title + struct-mode details grid.

The conto is rendered inside the default `.grouplet_grid_row` chrome
(card with border, drag handle, kebab — supplied by `grouplet.css`).
We just add:

  - a borderless textbox bound to `^.descr` that doubles as the
    account title (skin is in `editor_budget.css`)
  - a nested groupletGrid for the details, driven by `struct=` mode
    (Item 12 fakexcel: dark header, editable cells per dtype, live
    `formula=` cascade for the line total, totalize footer for the
    account total)

The `+` add cell uses `additem_class='grouplet_grid_footer--minimal'`
(compact, no dashed border). Per-row `×` uses the `--subtle` variant
so it does not visually compete with the spreadsheet cells.

Pattern reference: `test_06_struct_shopping_list` in
`test_grouplet_grid/01_gallery.py` — same recipe, scaled up to the
12-column budget schema and embedded inside the conto row.
"""
from gnr.web.gnrbaseclasses import BaseComponent


def _details_struct(struct):
    r = struct.view().rows()
    r.cell('tipo', name='Tipo', width='4.5em',
           values='ACQ:ACQ,CMP:CMP,RIS:RIS', edit=True)
    r.cell('descrizione', name='Descrizione', width='100%',
           edit=True, validate_notnull=True)
    r.cell('fase', name='Fase', width='8em',
           values='Preparazione:Preparazione,Riprese:Riprese,Post:Post',
           edit=True)
    r.cell('data_rif', name='Data rif.', width='8em',
           dtype='D', edit=True)
    r.cell('n_ris', name='N.Ris', width='4em',
           dtype='L', edit=True)
    r.cell('qty', name='Qt', width='4em',
           dtype='L', edit=True)
    r.cell('p_u', name='P.U.', width='6em',
           dtype='N', edit=True, format='#,##0.00')
    r.cell('iva', name='IVA', width='4.5em',
           values='0:0%,10:10%,22:22%', edit=True)
    r.cell('al_oneri', name='Al.Oneri', width='4.5em',
           values='0:0%,30:30%,33:33%', edit=True)
    r.cell('al_rit', name='Al.Rit.', width='4.5em',
           values='0:0%,20:20%,23:23%', edit=True)
    r.cell('distrib', name='Distribuz.', width='5em',
           values='UNI:UNI,FL:FL,QT:QT', edit=True)
    r.cell('tot_netto', name='Tot.Netto', width='7em',
           dtype='N', format='#,##0.00',
           formula='(qty || 1) * (p_u || 0)',
           totalize=True)


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Budget Account Card', priority=11)

    def grouplet_main(self, pane, **kwargs):
        # Inline header: numeric badge (^.codice, maintained by
        # `counterField`) + borderless title textbox. Same idiom as
        # `kanban_card` — styles live on the widget, no extra CSS class.
        head = pane.div(display='flex', align_items='center',
                        gap='8px', margin_bottom='6px',
                        padding_right='2em')
        head.div('^.codice',
                 font_family='ui-monospace, monospace',
                 font_weight='600', font_size='11px',
                 background='#16a085', color='white',
                 padding='2px 7px', border_radius='3px',
                 flex='0 0 auto')
        head.textbox(value='^.descr',
                     placeholder='!!Account description',
                     lbl=None,
                     font_weight='600', font_size='14px',
                     color='#16a085',
                     border='none', background='transparent',
                     padding='2px 4px', flex='1 1 auto',
                     width='100%')
        pane.groupletGrid(
            storepath='.details',
            struct=_details_struct,
            dragCode='budget_dettagli',
            additem_class='grouplet_grid_footer--minimal',
            additem_label='!!Add detail',
            delitem_kwargs=dict(
                _class='grouplet_grid_row_delete--subtle'),
            defaultRow=dict(tipo='ACQ', qty=1, p_u=0, iva=22))
        # Roll the account total up to `^.tot_conto` on the conto row
        # so the enclosing capitolo can sum it. `details.sum('tot_netto')`
        # walks the row Bag client-side and updates whenever any nested
        # detail changes.
        pane.dataFormula(
            '.tot_conto',
            'details ? details.sum("tot_netto") : 0',
            details='^.details')
