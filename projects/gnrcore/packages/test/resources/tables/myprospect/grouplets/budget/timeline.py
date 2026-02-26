from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Timeline', code='timeline', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.dateTextBox(value='^.desired_start', lbl='Desired Start Date')
        fb.dateTextBox(value='^.deadline', lbl='Hard Deadline')
        fb.filteringSelect(value='^.rollout_approach', lbl='Rollout Approach',
                           values='big_bang:Big Bang,phased:Phased,pilot:Pilot')
        fb.simpleTextArea(value='^.constraints', lbl='Constraints & Dependencies',
                          colspan=2, width='100%', height='60px')
