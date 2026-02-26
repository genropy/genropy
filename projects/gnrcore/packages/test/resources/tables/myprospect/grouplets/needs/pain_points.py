from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Pain Points', code='pain_points', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.main_challenges', lbl='Main Challenges',
                          colspan=2, width='100%', height='80px')
        fb.filteringSelect(value='^.urgency', lbl='Urgency',
                           values='low:Low,medium:Medium,high:High,critical:Critical')
        fb.filteringSelect(value='^.impact_area', lbl='Impact Area',
                           values='productivity:Productivity,costs:Costs,'
                                  'quality:Quality,compliance:Compliance')
        fb.simpleTextArea(value='^.workarounds', lbl='Current Workarounds',
                          colspan=2, width='100%', height='60px')
