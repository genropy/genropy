from gnr.web.gnrbaseclasses import BaseComponent
from gnrpkg.adm.app_store_helpers import app_store_links

info = {
    "code":'ios_qrcode',
    "caption":"!![en]Apple",
    "priority":1
}       

def is_enabled(page):
    return app_store_links.get_ios(page)
       

class Formlet(BaseComponent):
    def flt_main(self,pane):
        url = app_store_links.get_ios(self).get('store_url')
        pane.dataController(""";
            SET #WORKSPACE.qrcode_url = `/_tools/qrcode?text=${url}`;""",
            url=url,_onBuilt=True)
        flex = pane.flexbox(justify_content='center',align_items='center',margin_top='50px',flex_direction='column')
        link = flex.a(href=url,target="_blank")
        link.img(src='/_rsrc/pkg_adm/app_stores/ios_badge.svg',height='40px')
        flex.img(src='^#WORKSPACE.qrcode_url',height='200px',width='200px',border='0')
