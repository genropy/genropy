from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Error', code='error', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.error_code', lbl='Error Code')
        fb.textbox(value='^.error_message', lbl='Error Message')
        fb.simpleTextArea(value='^.log', lbl='Log',
                          colspan=2, width='100%', height='80px')
