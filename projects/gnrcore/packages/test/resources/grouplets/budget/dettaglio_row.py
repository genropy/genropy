"""Detail row grouplet — single row of 11 inline widgets.

Mirrors the inline budget detail editor in the Quick Budget mockup
(`mockup_editor_budget.html`). Each widget binds to a relative path
(`^.field`) on the row Bag. Layout is a horizontal CSS-grid; the
matching header lives in the parent groupletGrid's `top` slot and uses
the same grid-template-columns class so the columns stay aligned.

Field shape (matches the mockup table):
  tipo  descrizione    fase    data_rif    n_ris  qt   p_u   iva    al_oneri  al_rit   distrib   tot
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Budget Detail Row', priority=10)

    def grouplet_main(self, pane, **kwargs):
        # Single horizontal row, columns defined by the .gg-dettagli-grid
        # CSS class (also applied to the header in the top slot of the
        # parent groupletGrid). Putting the grid template in CSS keeps
        # header and rows pixel-aligned even if column widths change.
        row = pane.div(_class='gg-dettagli-grid gg-dettagli-row')
        # Tipo — 3-letter badge picker
        row.filteringSelect(
            value='^.tipo',
            values='ACQ:ACQ,CMP:CMP,RIS:RIS',
            _class='gg-dett-tipo')
        # Descrizione (free text)
        row.textbox(
            value='^.descrizione',
            placeholder='!!Description',
            _class='gg-dett-descr')
        # Fase
        row.filteringSelect(
            value='^.fase',
            values='Preparazione:Preparazione,'
                   'Riprese:Riprese,'
                   'Post:Post',
            _class='gg-dett-fase')
        # Data riferimento
        row.dateTextBox(
            value='^.data_rif',
            _class='gg-dett-data')
        # N. risorse
        row.numberTextBox(
            value='^.n_ris',
            placeholder='—',
            _class='gg-dett-num')
        # Quantità
        row.numberTextBox(
            value='^.qty',
            placeholder='1',
            _class='gg-dett-num')
        # Prezzo unitario
        row.numberTextBox(
            value='^.p_u',
            placeholder='0',
            _class='gg-dett-prezzo')
        # IVA
        row.filteringSelect(
            value='^.iva',
            values='0:0%,10:10%,22:22%',
            _class='gg-dett-iva')
        # Aliquota oneri
        row.filteringSelect(
            value='^.al_oneri',
            values='0:0%,30:30%,33:33%',
            _class='gg-dett-iva')
        # Aliquota ritenute
        row.filteringSelect(
            value='^.al_rit',
            values='0:0%,20:20%,23:23%',
            _class='gg-dett-iva')
        # Distribuzione
        row.filteringSelect(
            value='^.distrib',
            values='UNI:UNI,FL:FL,QT:QT',
            _class='gg-dett-distrib')
        # Totale netto — read-only, displays the pre-formatted string
        # computed by the dataFormula below.
        row.div(
            '^.tot_netto_fmt',
            _class='gg-dett-tot')
        # Compute tot_netto as a number, plus a formatted string for the
        # display div. Keeping the formula at the row level (not on the
        # page) means every nested row recomputes independently.
        pane.dataFormula(
            '.tot_netto',
            '(qty || 1) * (p_u || 0)',
            qty='^.qty',
            p_u='^.p_u')
        pane.dataFormula(
            '.tot_netto_fmt',
            'genro.formatter.asText(tot, {format: "#,##0.00"})',
            tot='^.tot_netto')
