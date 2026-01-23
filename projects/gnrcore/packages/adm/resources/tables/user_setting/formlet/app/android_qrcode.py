import urllib.parse
from gnr.web.gnrbaseclasses import BaseComponent


info = {
    "code":'android_qrcode',
    "caption":"!![en]Android",
    "priority":2
}       


def is_enabled(page):
    return page.application.config['mobile_app.android?store_url']

       
class Formlet(BaseComponent):
    def flt_main(self,pane):
        plain_url = self.application.config['mobile_app.android?store_url']
        url = urllib.parse.quote_plus(plain_url)
        pane.dataController(""";
            SET #WORKSPACE.qrcode_url = `${homeFolder}_tools/qrcode?url=${url}`;""",
            url=url,homeFolder='=gnr.homeFolder',_onBuilt=True)
        flex = pane.flexbox(justify_content='center',align_items='center',margin_top='50px',flex_direction='column')
        link = flex.a(href=plain_url,target="_blank")
        link.img(src='/_rsrc/pkg_adm/app_stores/android_badge.png',height='40px')
        flex.img(src='^#WORKSPACE.qrcode_url',height='200px',width='200px',border='0')
