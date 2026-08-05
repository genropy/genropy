from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Contract', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.contract_type', lbl='Contract Type',
                           values='new:New,renewal:Renewal,upgrade:Upgrade')
        fb.numberTextBox(value='^.duration_months', lbl='Duration (months)')
        fb.filteringSelect(value='^.sla_level', lbl='SLA Level',
                           values='basic:Basic,standard:Standard,premium:Premium')
