from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Timeline', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.dateTextBox(value='^.desired_start', lbl='Desired Start Date',
                       validate_notnull=True)
        fb.dateTextBox(value='^.deadline', lbl='Hard Deadline')
        fb.filteringSelect(value='^.rollout_approach', lbl='Rollout Approach',
                           validate_notnull=True,
                           values='big_bang:Big Bang,phased:Phased,pilot:Pilot')
        fb.simpleTextArea(value='^.constraints', lbl='Constraints & Dependencies',
                          validate_len='0:1000',
                          validate_len_message='Max 1000 characters',
                          colspan=2, width='100%', height='60px')
