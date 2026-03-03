import json
from gnr.web.gnrbaseclasses import BaseComponent

class Grouplet(BaseComponent):
    def __info__(self):
        return dict(code='connection_qrcode', caption='!![en]Connection', priority=3,
                    tags=None if self.site.is_mobile_app_enabled()  else 'notEnabled')



    def grouplet_main(self, pane, **kwargs):
        pane.dataController(""" const qrcode_text = `GENRO:${owner_name || sitename}:${url}`;
            SET .qrcode_url = `${url}_tools/qrcode?url=${qrcode_text}`;""",
            url='=gnr.homeFolder', sitename='=gnr.siteName',
            owner_name='=gnr.app_preference.adm.instance_data.owner_name', _onBuilt=True)
        with open(self.getResource('localized_texts.json', pkg='adm'), 'r', encoding='utf-8') as f:
            content_dict = json.loads(f.read())['app_qrcode']
        text = content_dict.get(self.language.lower()) or content_dict['en']
        pane.div(text, padding_left='20px', padding_right='20px',text_align='justify')
        pane.flexbox(justify_content='center', align_items='center',
                    margin_top='30px').img(src='^.qrcode_url',
                                           height='200px', width='200px', border='0')
