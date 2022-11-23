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

from builtins import object
class AppPref(object):
    def permission_adm(self, **kwargs):
        return 'admin'

    def prefpane_adm(self, parent, **kwargs):
        tc = parent.tabContainer(margin='2px',**kwargs)
        self._adm_general(tc.borderContainer(title='!!General'))
        #self._adm_mail(tc.contentPane(title='!!Mail options', datapath='.mail'))
        self._adm_backups(tc.contentPane(title='!!Backups', datapath='.backups'))
        self._adm_dev(tc.contentPane(title='!!Developers', datapath='.dev'))
        self._adm_helpdesk(tc.contentPane(title='!!Helpdesk', datapath='.helpdesk',_tags='_DEV_'))

    def _adm_helpdesk(self,pane):
        fb = pane.formbuilder(cols=1)
        fb.textbox(value='^.url',lbl='Url',width='40em')
        fb.textbox(value='^.user',lbl='User',width='20em')
        fb.textbox(value='^.password',lbl='Password',width='15em',type='password')
        fb.textbox(value='^.client_reference',lbl='Client reference')
        fb.textbox(value='^.documentation_url',lbl='Documentation url',width='40em')
        

    def _adm_dev(self,pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.checkbox(value='^.connection_log_enabled',label='Connection log enabled')
        fb.textbox(value='^.onlyoffice_secret',lbl='!![en]OnlyOffice integration secret')
        fb.textbox(value='^.onlyoffice_server',lbl='!![en]OnlyOffice Document server address')

    def _adm_general(self, bc):
        top = bc.contentPane(region='top')
        fb = top.formbuilder(cols=1,border_spacing='3px')
        fb.checkbox(value='^.general.forgot_password',label='Allow password recovery')
        fb.checkbox(value='^.general.new_user',label='New user registration')
        fb.textbox(value='^.general.password_regex',lbl='Password validate regex')
        if 'email' in self.db.packages:
            fb.dbSelect(value='^.mail.email_account_id',lbl='Default smtp account',dbtable='email.account')
        #fb.numberTextBox(value='^.screenlock_timeout',lbl='!!Screenlock timeout (minutes)')
        bc.appGuiCustomization(region='center',margin='2px',datapath='.gui_customization')
       


    def _adm_backups(self, pane):
        fb = pane.div(padding='5px').formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.backup_folder',lbl='Folder path')
        fb.numberTextBox(value='^.max_copies',lbl='Max copies')

    def _adm_mail(self, pane):
        fb = pane.div(margin='5px').formbuilder(cols=1, border_spacing='6px', width='100%', fld_width='100%',
                                                    tdl_width='10em')
        if 'email' in self.db.packages:
            fb.dbselect(value='^.email_account_id',lbl='Account',dbtable='email.account',hasDownArrow=True)
        
        fb.div(lbl='Mail Settings', colspan=2, lbl_font_style='italic', lbl_margin_top='1em', margin_top='1em',
               lbl_color='#7e5849',disabled='^.email_account_id')
        fb.textbox(value='^.smtp_host', lbl='SMTP Host', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.from_address', lbl='From address', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.user', lbl='Username', dtype='T',disabled='^.email_account_id')
        fb.textbox(value='^.password', lbl='Password', disabled='^.email_account_id', type='password')
        fb.textbox(value='^.port', lbl='Port', disabled='^.email_account_id')
        fb.checkbox(value='^.tls', lbl='TLS', dtype='B', disabled='^.email_account_id')
        fb.checkbox(value='^.ssl', lbl='SSL', dtype='B', disabled='^.email_account_id')
        fb.textbox(value='^.system_bcc', lbl='System bcc',disabled='^.email_account_id')

class UserPref(object):
    def prefpane_adm(self, parent, **kwargs):
        tc = parent.tabContainer(margin='2px',**kwargs)
        self._adm_general(tc.contentPane(title='!!General options', datapath='.general'))
        self._adm_mail(tc.contentPane(title='!!Mail options', datapath='.mail'))

    def _adm_general(self, pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px',margin='10px')
        #fb.numberTextBox(value='^.screenlock_timeout',lbl='!!Screenlock timeout (minutes)')
        fb.button('!!Change password',action="genro.mainGenroWindow.genro.publish('openNewPwd')")


    def _adm_mail(self, pane):
        fb = pane.div(margin='5px').formbuilder(cols=1, border_spacing='6px', width='100%', fld_width='100%')
        if 'email' in self.db.packages:
            fb.dbselect(value='^.email_account_id',lbl='Account',dbtable='email.account',hasDownArrow=True)
        fb.div(lbl='Mail Settings', colspan=2, lbl_font_style='italic', lbl_margin_top='1em', margin_top='1em',
               lbl_color='#7e5849')
        fb.textbox(value='^.smtp_host', lbl='SMTP Host', dtype='T', disabled='^.email_account_id')
        fb.textbox(value='^.from_address', lbl='From address', dtype='T', disabled='^.email_account_id')
        fb.textbox(value='^.user', lbl='Username', dtype='T', disabled='^.email_account_id')
        fb.textbox(value='^.password', lbl='Password', dtype='T', disabled='^.email_account_id', type='password')
        fb.textbox(value='^.port', lbl='Port', dtype='T', disabled='^.email_account_id')
        fb.checkbox(value='^.tls', lbl='TLS', dtype='B', disabled='^.email_account_id')
            
        