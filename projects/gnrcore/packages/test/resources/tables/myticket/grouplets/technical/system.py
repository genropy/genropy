from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='System', code='system', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.operating_system', lbl='Operating System',
                   colspan=2, width='100%')
        fb.textbox(value='^.software_version', lbl='Software Version')
        fb.textbox(value='^.browser', lbl='Browser')
