from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Goals', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.short_term_goals',
                          lbl='Short Term Goals (0-6 months)',
                          validate_notnull=True,
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.long_term_goals',
                          lbl='Long Term Goals (6-24 months)',
                          validate_notnull=True,
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.success_criteria', lbl='Success Criteria',
                          colspan=2, width='100%', height='60px')
