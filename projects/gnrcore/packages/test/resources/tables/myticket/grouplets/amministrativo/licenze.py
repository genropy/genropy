info = dict(caption='Licenze', code='licenze', priority=2)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.tipo_licenza', lbl='Tipo licenza',
                           values='trial:Trial,standard:Standard,enterprise:Enterprise')
        fb.numberTextBox(value='^.numero_utenti', lbl='Numero utenti')
        fb.dateTextBox(value='^.data_scadenza', lbl='Data scadenza')
