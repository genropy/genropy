from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Infrastructure', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.current_erp', lbl='Current ERP/CRM',
                   validate_notnull=True,
                   colspan=2, width='100%')
        fb.filteringSelect(value='^.hosting_model', lbl='Hosting',
                           validate_notnull=True,
                           values='on_premise:On Premise,cloud:Cloud,hybrid:Hybrid')
        fb.textbox(value='^.database', lbl='Database')
        fb.simpleTextArea(value='^.integrations', lbl='Existing Integrations',
                          colspan=2, width='100%', height='60px')
