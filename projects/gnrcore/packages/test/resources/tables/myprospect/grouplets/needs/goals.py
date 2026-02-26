from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Goals', code='goals', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.short_term_goals',
                          lbl='Short Term Goals (0-6 months)',
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.long_term_goals',
                          lbl='Long Term Goals (6-24 months)',
                          colspan=2, width='100%', height='60px')
        fb.simpleTextArea(value='^.success_criteria', lbl='Success Criteria',
                          colspan=2, width='100%', height='60px')
