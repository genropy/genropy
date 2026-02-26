from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Licenses', code='licenses', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.filteringSelect(value='^.license_type', lbl='License Type',
                           values='trial:Trial,standard:Standard,enterprise:Enterprise')
        fb.numberTextBox(value='^.user_count', lbl='User Count')
        fb.dateTextBox(value='^.expiry_date', lbl='Expiry Date')
