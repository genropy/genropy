from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    """Hand-written equivalent of the row template the JS adapter
    builds from the shopping-list struct of `test_9_struct_shopping_list`.

    Five widgets in a CSS grid mirroring `--gg-struct-columns:
    3em 14em 5em 7em 8em`. Used by `test_10_shopping_row_resource` as
    the visual baseline to compare against the struct= rendering."""

    def __info__(self):
        return dict(caption='Shopping Row (manual)', priority=3)

    def grouplet_main(self, pane, **kwargs):
        row = pane.div(_class='shopping_row',
                       display='grid',
                       grid_template_columns='3em 14em 5em 7em 8em',
                       gap='4px',
                       align_items='center')
        row.checkbox(value='^.bought')
        row.textbox(value='^.item', width='100%',
                    validate_notnull=True)
        row.numberTextBox(value='^.qty', width='100%')
        row.numberTextBox(value='^.unit_price', width='100%',
                          format='###,###,###.00')
        row.div(innerHTML='^.line_total',
                format='###,###,###.00',
                text_align='right')
