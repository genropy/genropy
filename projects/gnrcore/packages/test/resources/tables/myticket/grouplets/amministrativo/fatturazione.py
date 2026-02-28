info = dict(caption='Fatturazione', code='fatturazione', priority=1)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.numero_fattura', lbl='Numero fattura')
        fb.numberTextBox(value='^.importo', lbl='Importo')
        fb.dateTextBox(value='^.data_scadenza', lbl='Data scadenza')
