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



"""
Component for preference handling:
"""

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrlang import gnrImport


class BasePreferenceTabs(BaseComponent):
    def _pr_makePreferenceTabs(self,parent,packages='*',datapath=None,context_dbstore=None,wdg='tab',**kwargs):
        if isinstance(packages,str):
            packages = list(self.application.packages.keys()) if packages == '*' else packages.split(',')
        tc = getattr(parent,f'{wdg}Container')(datapath=datapath,context_dbstore=context_dbstore,nodeId='PREFROOT',**kwargs)
        for pkgId in packages:
            pkg = self.application.packages[pkgId]
            if pkg.disabled:
                continue
            permmissioncb = getattr(self, 'permission_%s' % pkg.id, None)
            auth = True
            if permmissioncb:
                auth = self.application.checkResourcePermission(permmissioncb(), self.userTags)
            panecb = getattr(self, 'prefpane_%s' % pkg.id, None)
            if panecb and auth:
                panecb(tc, title=pkg.attributes.get('name_full') or pkg.attributes.get('name_long') or pkg.id, datapath='.%s' % pkg.id, nodeId=pkg.id,
                        pkgId=pkg.id,_anchor=True,sqlContextRoot='%s.%s' % (datapath,pkg.id))
        return tc



class AppPrefHandler(BasePreferenceTabs):
    py_requires='preference:AppPref,foundation/tools'

    @struct_method
    def ph_appPreferencesTabs(self,parent,packages='*',datapath=None,context_dbstore=None,**kwargs):
        tc = self._pr_makePreferenceTabs(parent,packages=packages,datapath=datapath,
                                        context_dbstore=context_dbstore,**kwargs)
        if context_dbstore:
            tc.dataRpc(None,self.ph_updatePrefCache,formsubscribe_onSaved=True,prefdbstore=context_dbstore)
    
    @public_method
    def ph_updatePrefCache(self,prefdbstore=None,**kwargs):
        self.db.application.cache.updatedItem( '_storepref_%s' %prefdbstore)
    

    @struct_method
    def ph_appGuiCustomization(self,parent,**kwargs):
        tc = parent.tabContainer(**kwargs)
        self._ph_appGuiCustomization_login(tc.contentPane(title='!![en]Login customizations',datapath='.login',margin='2px'))
        self._ph_appGuiCustomization_templates(tc.tabContainer(title='!![en]E-mail templates',datapath='.login',margin='2px', tabPosition='left-h'))
        self._ph_appGuiCustomization_ownerLogoAndName(tc.contentPane(title='!![en]Owner name and images',datapath='.owner'))
        self._ph_appGuiCustomization_splashscreen(tc.contentPane(title='!!Splashscreen',datapath='.splashscreen'))
        #tc.contentPane(title='Themes')

    def _ph_appGuiCustomization_ownerLogoAndName(self, pane):
        fb = pane.div(margin='5px').formbuilder(cols=1, border_spacing='6px', width='100%',
                                                tdl_width='10em')
        fb.textbox(value='^#adm.instance_data.owner_name', lbl='!!Owner name',livePreference=True,width='100%')
        fb.img(src='^.cover_logo',src_back='.cover_logo_original', 
                        lbl='!!Cover logo', 
                        crop_border='2px dotted silver',
                        crop_width='250px',
                        crop_height='100px',
                        edit=True,
                        placeholder=True,
                        upload_folder='*')
        fb.img(src='^.square_logo',
                    src_back='.square_logo_original',
                     lbl='!!Square logo', 
                        crop_border='2px dotted silver',
                        crop_width='100px',
                        crop_height='100px',
                        edit=True,
                        takePicture=True,
                        placeholder=True,
                        upload_filename='favicon',
                        upload_folder='*')


    def _ph_appGuiCustomization_login(self,pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.login_title',width='30em',lbl='!![en]Login title',)
        fb.textbox(value='^.login_subtitle',width='30em',lbl='!![en]Login subtitle')
        fb.textbox(value='^.new_window_title',width='30em',lbl='!![en]New window title')
        fb.textbox(value='^.lost_password',width='30em',lbl='!![en]Lost password')
        fb.textbox(value='^.new_password',width='30em',lbl='!![en]New password')
        fb.textbox(value='^.check_email',width='30em',lbl='!![en]Check email')
        fb.textbox(value='^.confirm_user_title',width='30em',lbl='!![en]Confirm user title')
        fb.textbox(value='^.confirm_user_message',width='30em',lbl='!![en]Confirm user message')
        fb.textbox(value='^.new_user_ok_message',width='30em',lbl='!![en]New user ok message')
        fb.checkbox(value='^.login_flat',label='!![en]Flat login')
        
    def _ph_appGuiCustomization_templates(self,tc):
        self._auth_email_confirm_template(tc.borderContainer(title='!![en]New user'))
        self._auth_new_password_template(tc.borderContainer(title='!![en]Reset password'))

    def _auth_email_confirm_template(self,bc):
        fb = bc.contentPane(region='center').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^.tpl_userconfirm_id',lbl='!![en]New user tpl',
                        dbtable='adm.userobject',
                        condition='$objtype=:tp AND $tbl=:searchtbl',
                        condition_tp='template',
                        condition_searchtbl='adm.user',
                        hasDownArrow=True)
        fb.textbox(value='^.confirm_user_subject',width='30em',lbl='!![en]Subject',
                                                hidden='^.tpl_userconfirm_id',
                                                placeholder='!![en]Confirm user')
        fb.simpleTextArea(value='^.confirm_user_tpl',
                                                height='100px', 
                                                lbl='!![en]Message body',
                                                hidden='^.tpl_userconfirm_id', 
                                                placeholder='!![en]Dear $greetings to confirm click $link')
        
        bar = bc.contentPane(region='bottom').slotToolbar('*,sendtest')
        bar.sendtest.slotButton('!![en]Send test').dataRpc(self.sendTemplateTestEmail,
                                                           user_record='=gnr.user_record',
                                                           template_id='=.tpl_userconfirm_id',
                                                           subject='=.confirm_user_subject',
                                                           body='=.confirm_user_tpl')
        
    def _auth_new_password_template(self,bc):
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^.tpl_new_password_id',lbl='!![en]Reset password tpl',
                        dbtable='adm.userobject',
                        condition='$objtype=:tp AND $tbl=:searchtbl',
                        condition_tp='template',
                        condition_searchtbl='adm.user',
                        hasDownArrow=True)
        fb.textbox(value='^.confirm_password_subject',width='30em',lbl='!!Subject', 
                                                hidden='^.tpl_new_password_id',
                                                placeholder='!![en]Password recovery')
        fb.simpleTextArea(value='^.confirm_password_tpl',
                                                height='100px', 
                                                lbl='!![en]Message body',
                                                hidden='^.tpl_new_password_id',
                                                placeholder='!![en]Dear $greetings set your password $link')
        
        bar = bc.contentPane(region='bottom').slotToolbar('*,sendtest')
        bar.sendtest.slotButton('!![en]Send test').dataRpc(self.sendTemplateTestEmail,
                                                           user_record='=gnr.user_record',
                                                           template_id='=.tpl_new_password_id',
                                                           subject='=.confirm_password_subject',
                                                           body='=.confirm_password_tpl')

    @public_method
    def sendTemplateTestEmail(self, user_record=None, template_id=None, subject=None, body=None, **kwargs):
        user_record['link'] = self.externalUrlToken(self.site.homepage, userid=user_record['user_id'],max_usages=1)
        user_record['greetings'] = user_record['firstname'] or user_record['lastname']
        mailservice = self.getService('mail')
        if template_id:
            mailservice.sendUserTemplateMail(record_id=user_record, template_id=template_id,
                                                async_=False, html=True, scheduler=False)
        else:
            mailservice.sendmail_template(user_record, to_address=user_record['email'],
                                    body=body or 'Dear $greetings to confirm click $link', 
                                    subject=subject or 'Confirm user',
                                    async_=False, html=True, scheduler=False)


    def _ph_appGuiCustomization_splashscreen(self,pane):
        pass
 

class UserPrefHandler(BasePreferenceTabs):
    py_requires='preference:UserPref,foundation/tools'

    @struct_method
    def ph_userPreferencesTabs(self,parent,packages='*',datapath=None,context_dbstore=None,**kwargs):
        tc = self._pr_makePreferenceTabs(parent,packages=packages,datapath=datapath,context_dbstore=context_dbstore,**kwargs)
        if context_dbstore:
            tc.dataRpc(None,self.ph_updatePrefCache,formsubscribe_onSaved=True,prefdbstore=context_dbstore)
    
    @public_method
    def ph_updatePrefCache(self,prefdbstore=None,**kwargs):
        self.db.application.cache.updatedItem( '_storepref_%s' %prefdbstore)
    

class UserPrefMenu(BaseComponent):
    @struct_method
    def pm_userPrefMenu(self,parent,packages='*',iconClass=None):
        if isinstance(packages,str):
            packages = list(self.application.packages.keys()) if packages == '*' else packages.split(',')
        menu = parent.menudiv(iconClass='iconbox gear')

        for pkgId in packages:
            pkg = self.application.packages[pkgId]
            if pkg.disabled:
                continue
            m = gnrImport(self.getResource('preference',pkg=pkg.id,ext='py'),importAs=f'Pref_{pkg.id}')
            if not m:
                continue
            resource = getattr(m,'MenuUserPreference',None)
            instance = resource() if resource else None
            if not instance:
                continue
            instance._page = self
            linescb = [r for r in dir(instance) if not r.startswith('_')]
            if not linescb:
                continue
            m = menu.menuline(pkg.attributes['name_long']).menu()
            for cbname in linescb:
                h = getattr(instance,cbname)
                tags = getattr(h,'tags',None)
                if tags and not self.application.checkResourcePermission(tags, self.userTags):
                    continue
                pars = h()
                m.menuline(h.__doc__).dataController(pars.pop('action'),**pars)
        menu.menuline('-')
        menu.menuline('User preferences',action='genro.framedIndexManager.openUserPreferences()')


    @struct_method
    def pm_userSettings(self,parent,packages='*',iconClass=None):
        parent.slotButton('User settings',action='genro.framedIndexManager.openUserSettings()',
                            iconClass='iconbox gear')
