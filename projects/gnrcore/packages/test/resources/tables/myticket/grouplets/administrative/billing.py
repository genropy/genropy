from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Billing', code='billing', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.invoice_number', lbl='Invoice Number')
        fb.numberTextBox(value='^.amount', lbl='Amount')
        fb.dateTextBox(value='^.due_date', lbl='Due Date')
