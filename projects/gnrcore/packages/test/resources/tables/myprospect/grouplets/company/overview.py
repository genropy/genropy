from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Overview', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.industry', lbl='Industry',
                           validate_notnull=True,
                           values='technology:Technology,manufacturing:Manufacturing,'
                                  'services:Services,retail:Retail,healthcare:Healthcare,'
                                  'finance:Finance,other:Other')
        fb.filteringSelect(value='^.company_size', lbl='Company Size',
                           validate_notnull=True,
                           values='1_10:1-10,11_50:11-50,51_200:51-200,'
                                  '201_500:201-500,500_plus:500+')
        fb.textbox(value='^.website', lbl='Website', colspan=2, width='100%')
        fb.numberTextBox(value='^.annual_revenue', lbl='Annual Revenue',
                         validate_min=0,
                         validate_min_message='Revenue cannot be negative')
        fb.numberTextBox(value='^.year_founded', lbl='Year Founded',
                         validate_min=1800, validate_max=2026,
                         validate_min_message='Year too old',
                         validate_max_message='Year cannot be in the future')
