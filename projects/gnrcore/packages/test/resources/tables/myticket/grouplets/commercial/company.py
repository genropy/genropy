from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Company', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.company_name', lbl='Company',
                   colspan=2, width='100%')
        fb.textbox(value='^.industry', lbl='Industry')
        fb.filteringSelect(value='^.company_size', lbl='Size',
                           values='small:Small,medium:Medium,large:Large')
