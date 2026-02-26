from gnr.web.gnrbaseclasses import BaseComponent


info = {
    "code": 'android_qrcode',
    "caption": "!![en]Android",
    "priority": 2
}


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='6px')
        fb.textbox(value='^.app_name', lbl='App name',
                   colspan=2, width='100%')
        fb.textbox(value='^.package_name', lbl='Package name',
                   placeholder='com.example.myapp',
                   colspan=2, width='100%')
        fb.textbox(value='^.store_url', lbl='Play Store URL',
                   colspan=2, width='100%')
        fb.numberTextBox(value='^.min_sdk_version', lbl='Min SDK version',
                         placeholder='26')
        fb.filteringSelect(value='^.install_source', lbl='Install source',
                           values='playstore:Play Store,apk:Direct APK,enterprise:Enterprise')
