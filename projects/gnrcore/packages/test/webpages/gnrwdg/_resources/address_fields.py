class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.street', lbl='Street')
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.zip', lbl='ZIP')
        fb.textbox(value='^.country', lbl='Country')
