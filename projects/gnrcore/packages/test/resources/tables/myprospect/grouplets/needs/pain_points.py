from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Pain Points', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.main_challenges', lbl='Main Challenges',
                          validate_notnull=True,
                          colspan=2, width='100%', height='80px')
        fb.filteringSelect(value='^.urgency', lbl='Urgency',
                           validate_notnull=True,
                           values='low:Low,medium:Medium,high:High,critical:Critical')
        fb.filteringSelect(value='^.impact_area', lbl='Impact Area',
                           validate_notnull=True,
                           values='productivity:Productivity,costs:Costs,'
                                  'quality:Quality,compliance:Compliance')
        fb.simpleTextArea(value='^.workarounds', lbl='Current Workarounds',
                          colspan=2, width='100%', height='60px')
