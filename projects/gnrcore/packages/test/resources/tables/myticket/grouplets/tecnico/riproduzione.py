info = dict(caption='Riproduzione', code='riproduzione', priority=3)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.passi_riproduzione', lbl='Passi per riprodurre',
                          colspan=2, width='100%', height='80px')
        fb.textbox(value='^.risultato_atteso', lbl='Risultato atteso')
        fb.textbox(value='^.risultato_ottenuto', lbl='Risultato ottenuto')
