from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Error', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.error_code', lbl='Error Code')
        fb.textbox(value='^.error_message', lbl='Error Message')
        fb.simpleTextArea(value='^.log', lbl='Log',
                          colspan=2, width='100%', height='80px')
