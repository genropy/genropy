from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='!![en]Connection', priority=3)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='6px')
        fb.textbox(value='^.connection_name', lbl='Connection name',
                   colspan=2, width='100%')
        fb.textbox(value='^.server_url', lbl='Server URL',
                   placeholder='https://myserver.example.com',
                   colspan=2, width='100%')
        fb.numberTextBox(value='^.port', lbl='Port',
                         placeholder='443')
        fb.filteringSelect(value='^.protocol', lbl='Protocol',
                           values='https:HTTPS,http:HTTP,wss:WSS')
        fb.checkbox(value='^.auto_reconnect', label='Auto reconnect')
        fb.numberTextBox(value='^.timeout', lbl='Timeout (sec)',
                         placeholder='30')
