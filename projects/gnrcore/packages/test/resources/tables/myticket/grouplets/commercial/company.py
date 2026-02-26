from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Company', code='company', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.company_name', lbl='Company',
                   colspan=2, width='100%')
        fb.textbox(value='^.industry', lbl='Industry')
        fb.filteringSelect(value='^.company_size', lbl='Size',
                           values='small:Small,medium:Medium,large:Large')
