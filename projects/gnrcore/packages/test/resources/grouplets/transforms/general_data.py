from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(
            caption='General Data',
            priority=1
        )

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.DocumentType', lbl='Document Type')
        fb.textbox(value='^.Currency', lbl='Currency')
        fb.dateTextBox(value='^.Date', lbl='Date', colspan=2)
        fb.textbox(value='^.Number', lbl='Number')
        fb.numberTextBox(value='^.TotalDocumentAmount',
                         lbl='Total Amount', dtype='N')
