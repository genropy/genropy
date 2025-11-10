from gnr.web.gnrbaseclasses import BaseComponent
import json

info = {
    "code":'connection_qrcode',
    "caption":"!![en]Connection",
    "priority":3
}       
       
class Formlet(BaseComponent):
    def flt_main(self,pane):
        pane.dataController(""" const qrcode_text = `GENRO:${owner_name || sitename}:${url}`;
            SET #WORKSPACE.qrcode_url = `/_tools/qrcode?url=${qrcode_text}`;""",
            url='=gnr.homeFolder',sitename='=gnr.siteName',
            owner_name='=gnr.app_preference.adm.instance_data.owner_name',_onBuilt=True)
        with open(self.getResource('localized_texts.json',pkg='adm'), 'r', encoding='utf-8') as f:
            content_dict = json.loads(f.read())['app_qrcode']
        text = content_dict.get(self.language.lower()) or content_dict['en']
        pane.div(text,padding_left='10px',padding_right='10px')
        pane.flexbox(justify_content='center',align_items='center',margin_top='20px').img(src='^#WORKSPACE.qrcode_url',height='200px',width='200px',border='0')
