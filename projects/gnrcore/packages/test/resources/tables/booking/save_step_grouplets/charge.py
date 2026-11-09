from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Charge', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, table='test.booking')
        fb.field('payment_method', tag='filteringSelect',
                 values='card:Card,cash:Cash,transfer:Transfer')
        fb.field('total_amount', tag='numberTextBox')
