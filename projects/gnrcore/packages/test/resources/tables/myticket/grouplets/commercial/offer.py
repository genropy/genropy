from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Offer', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.estimated_budget', lbl='Estimated Budget')
        fb.dateTextBox(value='^.offer_deadline', lbl='Offer Deadline')
        fb.textbox(value='^.products_of_interest', lbl='Products of Interest',
                   colspan=2, width='100%')
