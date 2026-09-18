from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Rows', priority=2)

    def grouplet_main(self, pane, **kwargs):
        pane.div('Draft rows: product and qty are mandatory '
                 '(validate_notnull on grid editors).',
                 color='#666', font_style='italic', margin_bottom='6px')
        pane.groupletGrid(storepath='.extra_data.draft_rows',
                          resource='invoice_row',
                          additem_label='!!Add row',
                          delitem=True,
                          defaultRow=dict(product=None, qty=None,
                                          price=None))
        pane.div('Same rows through classic grid cell editors '
                 '(quickGrid, storepath on Bag).',
                 color='#666', font_style='italic',
                 margin='10px 0 6px 0')
        grid = pane.quickGrid(value='^.extra_data.draft_grid',
                              height='140px')
        grid.tools('addrow,delrow')
        grid.column('product', width='20em', name='Product',
                    edit=dict(validate_notnull=True))
        grid.column('qty', dtype='L', width='8em', name='Qty',
                    edit=dict(validate_notnull=True))
