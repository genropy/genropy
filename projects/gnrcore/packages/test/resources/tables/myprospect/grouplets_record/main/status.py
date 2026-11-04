from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Status', priority=3, locationpath='record',
                    mandatory='source')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, table='test.myprospect')
        fb.field('source')
        fb.field('status')
