from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Decision Process', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.decision_stage', lbl='Decision Stage',
                           validate_notnull=True,
                           values='research:Research,evaluation:Evaluation,'
                                  'shortlist:Shortlist,negotiation:Negotiation')
        fb.textbox(value='^.competitors', lbl='Competitors Evaluated',
                   colspan=2, width='100%')
        fb.simpleTextArea(value='^.selection_criteria',
                          lbl='Selection Criteria',
                          validate_notnull=True,
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.notes', lbl='Notes',
                          validate_len='0:2000',
                          validate_len_message='Max 2000 characters',
                          colspan=2, width='100%', height='60px')
