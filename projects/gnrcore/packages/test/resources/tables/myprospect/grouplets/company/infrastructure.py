from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Infrastructure', code='infrastructure', priority=3)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.current_erp', lbl='Current ERP/CRM',
                   colspan=2, width='100%')
        fb.filteringSelect(value='^.hosting_model', lbl='Hosting',
                           values='on_premise:On Premise,cloud:Cloud,hybrid:Hybrid')
        fb.textbox(value='^.database', lbl='Database')
        fb.simpleTextArea(value='^.integrations', lbl='Existing Integrations',
                          colspan=2, width='100%', height='60px')
