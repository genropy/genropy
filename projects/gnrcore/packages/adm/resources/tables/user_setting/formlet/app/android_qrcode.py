from gnr.web.gnrbaseclasses import BaseComponent
import json

info = {
    "code":'android_qrcode',
    "caption":"!![en]Android",
    "priority":2
}       


def get_url(page):
    mainpackage = page.db.application.site.mainpackage
    with open(page.getResource('app_store_links.json',pkg=mainpackage), 'r', encoding='utf-8') as f:
        stores_dict = json.loads(f.read())
    if not stores_dict:
        return False
    link = stores_dict.get('android')
    return link or False

def is_enabled(page):
    return get_url(page)

       
class Formlet(BaseComponent):
    def flt_main(self,pane):
        url = get_url(self)
        pane.dataController(""";
            SET #WORKSPACE.qrcode_url = `/_tools/qrcode?text=${url}`;""",
            url=url,_onBuilt=True)
        flex = pane.flexbox(justify_content='center',align_items='center',margin_top='50px',flex_direction='column')
        link = flex.a(href=url,target="_blank")
        link.img(src='/_rsrc/pkg_adm/app_stores/android_badge.png',height='40px')
        flex.img(src='^#WORKSPACE.qrcode_url',height='200px',width='200px',border='0')
