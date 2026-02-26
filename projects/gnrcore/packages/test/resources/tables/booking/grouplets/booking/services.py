from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Services', code='services', priority=3)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2,table='test.booking')
        fb.field('breakfast', tag='checkbox', lbl='Breakfast')
        fb.field('parking', tag='checkbox', lbl='Parking')
        fb.field('spa', tag='checkbox', lbl='Spa')
        fb.field('notes', tag='simpleTextArea', lbl='Notes',
                 colspan=2, width='100%', height='80px')
