from gnr.web.gnrbaseclasses import BaseComponent


info = {
    "code": 'ios_qrcode',
    "caption": "!![en]Apple iOS",
    "priority": 1
}


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='6px')
        fb.textbox(value='^.app_name', lbl='App name',
                   colspan=2, width='100%')
        fb.textbox(value='^.bundle_id', lbl='Bundle ID',
                   placeholder='com.example.myapp',
                   colspan=2, width='100%')
        fb.textbox(value='^.store_url', lbl='App Store URL',
                   colspan=2, width='100%')
        fb.textbox(value='^.min_ios_version', lbl='Min iOS version',
                   placeholder='16.0')
        fb.filteringSelect(value='^.device_target', lbl='Device',
                           values='iphone:iPhone,ipad:iPad,universal:Universal')
