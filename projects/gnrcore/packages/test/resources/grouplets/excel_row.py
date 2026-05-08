from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Excel-style Row', priority=2)

    def grouplet_main(self, pane, **kwargs):
        row = pane.div(display='flex', gap='8px', align_items='center',
                       flex_wrap='wrap')
        row.textbox(value='^.product', placeholder='Product',
                    width='150px', flex='1 1 150px',
                    validate_notnull=True)
        row.numberTextBox(value='^.qty', placeholder='Qty',
                          width='60px', validate_notnull=True)
        row.numberTextBox(value='^.price', placeholder='Price',
                          width='80px')
        row.textbox(value='^.notes', placeholder='Notes',
                    width='160px', flex='1 1 160px')
