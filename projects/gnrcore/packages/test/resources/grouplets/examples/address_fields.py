class Grouplet(object):
    def __info__(self):
        return dict(caption='Address Fields', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, border_spacing='3px')
        fb.textbox(value='^.street', lbl='Street')
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.zip', lbl='ZIP')
        fb.textbox(value='^.country', lbl='Country')
