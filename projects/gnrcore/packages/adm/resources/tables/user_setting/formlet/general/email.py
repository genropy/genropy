from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata

info = {
    "code":'email',
    "caption":"!![en]Email",
    "priority":1,
    "legacy_path":"adm"
}

class Formlet(BaseComponent):
    def flt_main(self,pane):
        fb = pane.formlet(cols=1)
        if 'email' in self.db.packages:
            fb.dbselect(value='^.email_account_id',lbl='!![en]Account',dbtable='email.account',hasDownArrow=True)
        
        fb.div(lbl='!![en]Mail Settings', colspan=1, lbl_font_style='italic', lbl_margin_top='1em', margin_top='1em',
               lbl_color='#7e5849',disabled='^.email_account_id')
        fb.textbox(value='^.smtp_host', lbl='!![en]SMTP Host', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.from_address', lbl='!![en]From address', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.user', lbl='!![en]Username', dtype='T',disabled='^.email_account_id')
        fb.passwordTextBox(value='^.password', lbl='!![en]Password', disabled='^.email_account_id')
        fb.textbox(value='^.port', lbl='Port', disabled='^.email_account_id')
        fb.checkbox(value='^.tls', lbl='TLS', dtype='B', disabled='^.email_account_id')
        fb.checkbox(value='^.ssl', lbl='SSL', dtype='B', disabled='^.email_account_id')
        fb.textbox(value='^.system_bcc', lbl='System bcc',disabled='^.email_account_id')

