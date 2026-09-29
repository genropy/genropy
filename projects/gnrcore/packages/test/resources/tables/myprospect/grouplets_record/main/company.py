from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Company', priority=1, locationpath='record')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, table='test.myprospect')
        fb.field('company_name')
        fb.field('contact_name')
