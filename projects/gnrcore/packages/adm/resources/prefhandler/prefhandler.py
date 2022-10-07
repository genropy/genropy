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

from past.builtins import basestring
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrbag import Bag,BagResolver
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwebstruct import struct_method


class BasePreferenceTabs(BaseComponent):
    def _pr_makePreferenceTabs(self,parent,packages='*',datapath=None,context_dbstore=None,wdg='tab',**kwargs):
        if isinstance(packages,basestring):
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
        self._ph_appGuiCustomization_login(tc.tabContainer(title='!!Login personalizations',datapath='.login',margin='2px',tabPosition="left-h"))
        self._ph_appGuiCustomization_ownerLogoAndName(tc.contentPane(title='!!Owner name and images',datapath='.owner'))
        self._ph_appGuiCustomization_splashscreen(tc.contentPane(title='!!Splashscreen',datapath='.splashscreen'))
        #tc.contentPane(title='Themes')

    def _ph_appGuiCustomization_ownerLogoAndName(self, pane):
        fb = pane.div(margin='5px').formbuilder(cols=1, border_spacing='6px', width='100%', fld_width='100%',
                                                tdl_width='10em')
        fb.textbox(value='^.owner_name', lbl='!!Owner name',livePreference=True)
        fb.img(src='^.logo_url',src_back='.logo_original', 
                        lbl='!!Logo image', 
                        border='2px dotted silver',
                        crop_width='478px',
                        crop_height='100px',
                        edit=True,
                        placeholder=True,
                        upload_folder='*')
        fb.button('!![en]Remove', hidden='^.logo_url?=!#v').dataController("SET .logo_url = null;")
        fb.img(src='^.favicon_url',
                    src_back='.favicon_url_original',
                     lbl='!!Favicon', 
                        border='2px dotted silver',
                        crop_width='256px',
                        crop_height='256px',
                        edit=True,
                        placeholder=True,
                        upload_filename='favicon',
                        upload_folder='*')
        fb.button('!![en]Remove', hidden='^.favicon_url?=!#v').dataController("SET .favicon_url = null;")


    def _ph_appGuiCustomization_login(self,tc):
        pane = tc.contentPane(title='Caption and messages')
        fb = pane.formbuilder(cols=1,border_spacing='3px')

        fb.textbox(value='^.login_title',width='30em',lbl='Login title',)
        fb.textbox(value='^.login_subtitle',width='30em',lbl='Login subtitle')
        fb.textbox(value='^.new_window_title',width='30em',lbl='New window title')
        fb.textbox(value='^.lost_password',width='30em',lbl='!!Lost password')
        fb.textbox(value='^.new_password',width='30em',lbl='New password')
        fb.textbox(value='^.check_email',width='30em',lbl='Check email')
        fb.textbox(value='^.confirm_user_title',width='30em',lbl='Confirm user title')
        fb.textbox(value='^.confirm_user_message',width='30em',lbl='Confirm user message')
        fb.textbox(value='^.new_user_ok_message',width='30em',lbl='New user ok message')
        fb.checkbox(value='^.login_flat',label='Flat login')
        self._auth_email_confirm_template(tc.borderContainer(title='!!Confirm user template'))
        self._auth_new_password_template(tc.borderContainer(title='!!Confirm new password template'))

    def _auth_email_confirm_template(self,bc):
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^.tpl_userconfirm_id',lbl='!![en]Confirm user template',
                        dbtable='adm.userobject',
                        condition='$objtype=:tp AND $tbl=:searchtbl',
                        condition_tp='template',
                        condition_searchtbl='adm.user',
                        hasDownArrow=True)
        fb.textbox(value='^.confirm_user_subject',width='30em',lbl='!!Subject',
                                                hidden='^.tpl_userconfirm_id')
        bc.contentPane(region='center').simpleTextArea(value='^.confirm_user_tpl',editor=True)

    def _auth_new_password_template(self,bc):
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^.tpl_new_password_id',lbl='!![en]New password template',
                        dbtable='adm.userobject',
                        condition='$objtype=:tp AND $tbl=:searchtbl',
                        condition_tp='template',
                        condition_searchtbl='adm.user',
                        hasDownArrow=True)
        fb.textbox(value='^.confirm_password_subject',width='30em',lbl='!!Subject', hidden='^.tpl_new_password_id')
        bc.contentPane(region='center').simpleTextArea(value='^.confirm_password_tpl',editor=True)

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
    
        