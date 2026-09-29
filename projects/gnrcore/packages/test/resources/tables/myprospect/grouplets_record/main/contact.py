from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Contact', priority=2, locationpath='record')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, table='test.myprospect')
        fb.field('contact_email')
        fb.field('contact_phone')
