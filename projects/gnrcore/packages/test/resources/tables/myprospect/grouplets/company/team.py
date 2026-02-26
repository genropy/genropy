from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Team', code='team', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.decision_maker', lbl='Decision Maker',
                   colspan=2, width='100%')
        fb.textbox(value='^.decision_maker_role', lbl='Role')
        fb.textbox(value='^.technical_contact', lbl='Technical Contact')
        fb.numberTextBox(value='^.it_team_size', lbl='IT Team Size')
        fb.filteringSelect(value='^.tech_maturity', lbl='Tech Maturity',
                           values='low:Low,medium:Medium,high:High')
