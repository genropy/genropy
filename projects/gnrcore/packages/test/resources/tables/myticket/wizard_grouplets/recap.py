from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Recap', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px',
                          table='test.myticket')
        fb.field('description', width='100%', tag='simpleTextArea',
                 height='80px')
