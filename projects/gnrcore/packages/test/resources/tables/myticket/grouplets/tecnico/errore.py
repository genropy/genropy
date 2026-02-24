info = dict(caption='Errore', code='errore', priority=2)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.codice_errore', lbl='Codice errore')
        fb.textbox(value='^.messaggio_errore', lbl='Messaggio errore')
        fb.simpleTextArea(value='^.log', lbl='Log',
                          colspan=2, width='100%', height='80px')
