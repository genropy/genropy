from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Anagrafica', code='anagrafica', priority=1)

class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px', table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('denominazione_tedesca', colspan=2, width='100%')
        fb.field('capoluogo')
