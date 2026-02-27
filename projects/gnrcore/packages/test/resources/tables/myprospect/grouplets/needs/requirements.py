from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Requirements', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.checkbox(value='^.need_reporting', lbl='Reporting & Analytics')
        fb.checkbox(value='^.need_automation', lbl='Workflow Automation')
        fb.checkbox(value='^.need_integration', lbl='Third-Party Integration')
        fb.checkbox(value='^.need_mobile', lbl='Mobile Access')
        fb.checkbox(value='^.need_multiuser', lbl='Multi-User Collaboration')
        fb.checkbox(value='^.need_security', lbl='Advanced Security')
        fb.simpleTextArea(value='^.other_requirements',
                          lbl='Other Requirements',
                          validate_len='0:500',
                          validate_len_message='Max 500 characters',
                          colspan=2, width='100%', height='60px')
