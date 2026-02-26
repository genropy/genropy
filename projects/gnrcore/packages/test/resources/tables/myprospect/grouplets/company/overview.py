from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Overview', code='overview', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.industry', lbl='Industry',
                           values='technology:Technology,manufacturing:Manufacturing,'
                                  'services:Services,retail:Retail,healthcare:Healthcare,'
                                  'finance:Finance,other:Other')
        fb.filteringSelect(value='^.company_size', lbl='Company Size',
                           values='1_10:1-10,11_50:11-50,51_200:51-200,'
                                  '201_500:201-500,500_plus:500+')
        fb.textbox(value='^.website', lbl='Website', colspan=2, width='100%')
        fb.numberTextBox(value='^.annual_revenue', lbl='Annual Revenue')
        fb.numberTextBox(value='^.year_founded', lbl='Year Founded')
