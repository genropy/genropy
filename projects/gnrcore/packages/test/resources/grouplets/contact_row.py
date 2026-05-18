"""Contact channel row — channel type + value (e.g. email/phone/web)."""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Contact Channel', priority=21)

    def grouplet_main(self, pane, **kwargs):
        row = pane.div(display='flex', gap='8px', align_items='center')
        row.filteringSelect(
            value='^.channel',
            values='email:Email,phone:Phone,mobile:Mobile,'
                   'web:Web,linkedin:LinkedIn,other:Other',
            width='110px',
            lbl=None)
        row.textbox(value='^.value', placeholder='!!Value',
                    flex='1 1 auto', lbl=None)
