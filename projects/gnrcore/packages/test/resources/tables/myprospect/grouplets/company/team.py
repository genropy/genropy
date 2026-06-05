from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Team', priority=2)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.decision_maker', lbl='Decision Maker',
                   validate_notnull=True,
                   colspan=2, width='100%')
        fb.textbox(value='^.decision_maker_role', lbl='Role',
                   validate_notnull=True)
        fb.textbox(value='^.technical_contact', lbl='Technical Contact')
        fb.numberTextBox(value='^.it_team_size', lbl='IT Team Size',
                         validate_min=1,
                         validate_min_message='Must have at least 1 person')
        fb.filteringSelect(value='^.tech_maturity', lbl='Tech Maturity',
                           validate_notnull=True,
                           values='low:Low,medium:Medium,high:High')
