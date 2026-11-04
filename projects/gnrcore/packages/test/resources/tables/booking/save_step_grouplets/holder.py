from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Holder', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, table='test.booking')
        fb.field('guest_name', validate_notnull=True, width='100%')
        fb.field('guest_email', width='100%')
