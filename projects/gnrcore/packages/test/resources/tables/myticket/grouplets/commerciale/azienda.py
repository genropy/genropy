info = dict(caption='Azienda', code='azienda', priority=1)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.nome_azienda', lbl='Azienda',
                   colspan=2, width='100%')
        fb.textbox(value='^.settore', lbl='Settore')
        fb.filteringSelect(value='^.dimensione', lbl='Dimensione',
                           values='piccola:Piccola,media:Media,grande:Grande')
