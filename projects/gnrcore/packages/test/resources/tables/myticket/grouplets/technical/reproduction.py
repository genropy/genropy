from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Reproduction', code='reproduction', priority=3)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.steps_to_reproduce', lbl='Steps to Reproduce',
                          colspan=2, width='100%', height='80px')
        fb.textbox(value='^.expected_result', lbl='Expected Result')
        fb.textbox(value='^.actual_result', lbl='Actual Result')
