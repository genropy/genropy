from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Shipping', priority=2,
                    template='<div>${<span>$ship_city</span>}${<span> · $ship_carrier</span>}</div>'
                             '${<div>Notes: $ship_notes</div>}')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='6px')
        fb.textbox(value='^.ship_city', lbl='City', width='100%')
        fb.filteringSelect(value='^.ship_carrier', lbl='Carrier',
                           values='DHL:DHL,UPS:UPS,GLS:GLS')
        fb.textbox(value='^.ship_notes', lbl='Notes', width='100%')
