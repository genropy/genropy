info = dict(caption='Contratto', code='contratto', priority=3)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.tipo_contratto', lbl='Tipo contratto',
                           values='nuovo:Nuovo,rinnovo:Rinnovo,upgrade:Upgrade')
        fb.numberTextBox(value='^.durata_mesi', lbl='Durata (mesi)')
        fb.filteringSelect(value='^.livello_sla', lbl='Livello SLA',
                           values='base:Base,standard:Standard,premium:Premium')
