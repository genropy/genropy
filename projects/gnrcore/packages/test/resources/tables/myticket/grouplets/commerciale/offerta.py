info = dict(caption='Offerta', code='offerta', priority=2)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.budget_previsto', lbl='Budget previsto')
        fb.dateTextBox(value='^.scadenza_offerta', lbl='Scadenza offerta')
        fb.textbox(value='^.prodotti_interesse', lbl='Prodotti di interesse',
                   colspan=2, width='100%')
