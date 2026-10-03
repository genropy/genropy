from gnr.web.gnrbaseclasses import BaseComponent

SHIPMENT_KINDS = [
    dict(code='STD', description='Standard', note='3-5 working days', sign=1),
    dict(code='EXP', description='Express', note='Next working day', sign=1),
    dict(code='PIK', description='Pick-up', note='Collect at the warehouse', sign=1),
    dict(code='RET', description='Return', note='Goods sent back by the customer', sign=-1),
    dict(code='CRN', description='Credit note', note='Refund without goods', sign=-1),
]


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Kind', priority=1, autoNext=True,
                    template='$kind · $kind_description')

    def grouplet_main(self, pane, **kwargs):
        pane.groupletChoice(field='kind', rows=SHIPMENT_KINDS, value_column='code',
                            glyph='code', title='description', note='$note',
                            caption_field='kind_description',
                            groups=[dict(condition=lambda r: r['sign'] > 0),
                                    dict(caption='Returns and refunds',
                                         condition=lambda r: r['sign'] < 0)])
