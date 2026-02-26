from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Decision Process', code='decision', priority=3)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.decision_stage', lbl='Decision Stage',
                           values='research:Research,evaluation:Evaluation,'
                                  'shortlist:Shortlist,negotiation:Negotiation')
        fb.textbox(value='^.competitors', lbl='Competitors Evaluated',
                   colspan=2, width='100%')
        fb.simpleTextArea(value='^.selection_criteria',
                          lbl='Selection Criteria',
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.notes', lbl='Notes',
                          colspan=2, width='100%', height='60px')
