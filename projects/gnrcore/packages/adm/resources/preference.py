# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
try:
    import pyotp
except ImportError:
    pyotp = None
    
class AppPref(object):
    def permission_adm(self, **kwargs):
        return 'admin'

    def prefpane_adm(self, parent, **kwargs):
        tc = parent.tabContainer(margin='2px',**kwargs)
        self._adm_general(tc.borderContainer(title='!!General'))
        self._adm_backups(tc.contentPane(title='!!Backups', datapath='.backups'))
        self._adm_dev(tc.contentPane(title='!!Developers', datapath='.dev'))
        self._adm_helpdesk(tc.contentPane(title='!!Helpdesk', datapath='.helpdesk',_tags='_DEV_'))
        self._adm_privacy(tc.borderContainer(title='!!Privacy', datapath='.privacy'))
        self._adm_testing(tc.contentPane(title='!!Testing', datapath='.testing',_tags='superadmin'))

    def _adm_testing(self,pane):
        fb = pane.formbuilder()
        fb.dbselect(value='^.beta_tester_tag',table='adm.htag',width='Beta tester tag',
                    condition='$child_count=0',alternatePkey='authorization_tag',
                    hasDownArrow=True,lbl='Beta tester')
        fb.textbox(value='^.test_deny_message',lbl='!![en]Deny message')

    def _adm_helpdesk(self,pane):
        fb = pane.formbuilder(cols=1)
        fb.textbox(value='^.url',lbl='!![en]Url',width='40em')
        fb.textbox(value='^.user',lbl='!![en]User',width='20em')
        fb.textbox(value='^.password',lbl='!![en]Password',width='15em',type='password')
        fb.textbox(value='^.client_reference',lbl='!![en]Client reference')
        fb.textbox(value='^.documentation_url',lbl='!![en]Documentation url',width='40em')
        
    def _adm_privacy(self, bc):
        self.mixinComponent('privacy:PrivacyPreferencePane')
        self.privacyPreferencePane(bc)

    def _adm_dev(self,pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.checkbox(value='^.connection_log_enabled',label='!![en]Connection log enabled')

    def _adm_general(self, bc):
        top = bc.contentPane(region='top')
        fb = top.formbuilder(cols=1,border_spacing='3px')
        fb.checkbox(value='^.general.forgot_password',label='!![en]Allow password recovery')
        fb.checkbox(value='^.general.new_user',label='!![en]New user registration')
        if pyotp:
            fb.checkbox(value='^.general.2fa_enabled',label='!![en]2FA authentication')

        fb.textbox(value='^.general.password_regex',lbl='!![en]Password validate regex')
        if 'email' in self.db.packages:
            fb.dbSelect(value='^.mail.email_account_id',lbl='!![en]Default smtp account',dbtable='email.account')
        #DP Deprecated, soon to be removed
        bc.appGuiCustomization(region='center',margin='2px',datapath='.gui_customization')

    def _adm_backups(self, pane):
        fb = pane.div(padding='5px').formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.backup_folder',lbl='!![en]Folder path', placeholder='home:maintenance')
        fb.numberTextBox(value='^.max_copies',lbl='!![en]Max copies')

class UserPref(object):
    
    def prefpane_adm(self, parent, **kwargs):
        pane = parent.contentPane(**kwargs)
        fb = pane.div(margin_right='20px').formbuilder(cols=1, border_spacing='6px', width='100%', fld_width='100%',colswidth='auto')
        if 'email' in self.db.packages:
            fb.dbselect(value='^.email_account_id',lbl='!![en]Account',dbtable='email.account',hasDownArrow=True)
        
        fb.div(lbl='!![en]Mail Settings', colspan=2, lbl_font_style='italic', lbl_margin_top='1em', margin_top='1em',
               lbl_color='#7e5849',disabled='^.email_account_id')
        fb.textbox(value='^.smtp_host', lbl='!![en]SMTP Host', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.from_address', lbl='!![en]From address', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.user', lbl='!![en]Username', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.password', lbl='!![en]Password', disabled='^.email_account_id', type='password')
        fb.textbox(value='^.port', lbl='Port', disabled='^.email_account_id')
        fb.checkbox(value='^.tls', lbl='TLS', dtype='B', disabled='^.email_account_id')
        fb.checkbox(value='^.ssl', lbl='SSL', dtype='B', disabled='^.email_account_id')
        fb.textbox(value='^.system_bcc', lbl='System bcc',disabled='^.email_account_id')
    