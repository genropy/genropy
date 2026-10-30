from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Details', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='6px')
        fb.div('^.kind_description', lbl='Kind')
        fb.textbox(value='^.reference', lbl='Reference', width='100%')
