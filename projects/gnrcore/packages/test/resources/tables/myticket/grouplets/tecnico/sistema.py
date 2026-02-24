info = dict(caption='Sistema', code='sistema', priority=1)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.sistema_operativo', lbl='Sistema operativo',
                   colspan=2, width='100%')
        fb.textbox(value='^.versione_software', lbl='Versione software')
        fb.textbox(value='^.browser', lbl='Browser')
