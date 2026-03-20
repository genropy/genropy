from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(
            caption='Dati Generali',
            priority=1
        )

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.TipoDocumento', lbl='Tipo Documento')
        fb.textbox(value='^.Divisa', lbl='Divisa')
        fb.dateTextBox(value='^.Data', lbl='Data', colspan=2)
        fb.textbox(value='^.Numero', lbl='Numero')
        fb.numberTextBox(value='^.ImportoTotaleDocumento',
                         lbl='Importo Totale', dtype='N')
