from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Financials', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.budget_range', lbl='Budget Range',
                           validate_notnull=True,
                           values='under_5k:Under 5K,5k_20k:5K-20K,'
                                  '20k_50k:20K-50K,50k_100k:50K-100K,'
                                  'over_100k:Over 100K')
        fb.filteringSelect(value='^.budget_status', lbl='Budget Status',
                           validate_notnull=True,
                           values='approved:Approved,pending:Pending Approval,'
                                  'not_allocated:Not Yet Allocated')
        fb.filteringSelect(value='^.payment_preference', lbl='Payment Preference',
                           values='monthly:Monthly,annual:Annual,one_time:One-Time')
        fb.numberTextBox(value='^.expected_roi_months',
                         lbl='Expected ROI (months)',
                         validate_min=1, validate_max=60,
                         validate_min_message='Must be at least 1 month',
                         validate_max_message='Max 60 months')
