from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Codici', code='codici', priority=2,
            template='<div><b>$sigla_provincia</b> - $codice_comune</div>')


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px', table='glbl.comune')
        fb.field('sigla_provincia')
        fb.field('codice_comune')
        fb.field('codice_provincia')
        fb.field('codice_regione')
