"""Shipping address grouplet whose card profile lives in the resource."""
from gnr.web.gnrbaseclasses import BaseComponent

TEMPLATE = '$city${ · $province}'


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Shipping address', template=TEMPLATE,
                    card=dict(collapsible=True, delitem=True, tools='collapse,title,doc,menu',
                              doc='file:card_profile_doc.html',
                              doc_kw=dict(courier='Fast Parcel')))

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.street', lbl='Street', colspan=2)
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.province', lbl='Province', width='4em')
