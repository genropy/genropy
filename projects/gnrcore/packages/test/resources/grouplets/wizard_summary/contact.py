from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Contact', priority=1,
                    template='${<b>$contact_name</b>}${<span> · $contact_email</span>}')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='6px')
        fb.textbox(value='^.contact_name', lbl='Name', width='100%')
        fb.textbox(value='^.contact_email', lbl='Email', width='100%')
