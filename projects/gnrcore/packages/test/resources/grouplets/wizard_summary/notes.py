from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Notes', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='6px')
        fb.simpleTextArea(value='^.final_notes', lbl='Notes',
                          width='100%', height='60px')
