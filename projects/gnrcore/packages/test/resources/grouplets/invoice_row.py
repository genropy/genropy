from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Invoice Row', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=4, border_spacing='4px')
        fb.textbox(value='^.product', lbl='Product',
                   colspan=2, width='100%',
                   validate_notnull=True,
                   validate_notnull_error='!!Product is required')
        fb.numberTextBox(value='^.qty', lbl='Qty', width='5em',
                         validate_notnull=True)
        fb.numberTextBox(value='^.price', lbl='Price', width='6em')
        fb.textbox(value='^.note', lbl='Note',
                   colspan=4, width='100%')
