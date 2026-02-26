from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Financials', code='financials', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.budget_range', lbl='Budget Range',
                           values='under_5k:Under 5K,5k_20k:5K-20K,'
                                  '20k_50k:20K-50K,50k_100k:50K-100K,'
                                  'over_100k:Over 100K')
        fb.filteringSelect(value='^.budget_status', lbl='Budget Status',
                           values='approved:Approved,pending:Pending Approval,'
                                  'not_allocated:Not Yet Allocated')
        fb.filteringSelect(value='^.payment_preference', lbl='Payment Preference',
                           values='monthly:Monthly,annual:Annual,one_time:One-Time')
        fb.numberTextBox(value='^.expected_roi_months',
                         lbl='Expected ROI (months)')
