from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Payment', priority=4)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2,table='test.booking')
        fb.field('payment_method', tag='filteringSelect',
                 values='credit_card:Credit Card,bank_transfer:Bank Transfer,cash:Cash',
                 lbl='Payment Method', validate_notnull=True)
        fb.field('card_holder', lbl='Card Holder')
        fb.field('total_amount', tag='numberTextBox', lbl='Total Amount',
                 validate_notnull=True)
