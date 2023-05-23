# -*- coding: utf-8 -*-

# th_user.py
# Created by Saverio Porcari on 2011-03-13.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method,customizable
from gnr.core.gnrbag import Bag
import urllib
try:
    import pyotp
except ImportError:
    pyotp = None

class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('username',name='Username',width='10em')
        r.fieldcell('fullname',name='Fullname',width='20em')
        r.fieldcell('group_code')
        r.fieldcell('email',name='Email',width='20em')
        r.fieldcell('@tags.@tag_id.code',name='Tags',width='100%')
        r.fieldcell('auth_tags',name='Old tags',width='15em')

   #def th_bottom_main(self, bottom):
   #    bar = bottom.slotToolbar('5,user_importer,*')
   #    bar.user_importer.div(_tags='admin',
   #                        margin_top='1px').paletteImporter(paletteCode='importUsers',
   #                        dockButton_iconClass='iconbox import_data_tool',
   #                        title='!!Import users from Excel/CSV',
   #                        importButton_label='Import users',
   #                        previewLimit=50,
   #                        #errorCb='vendita_js.erroreImportRichiesta(error)',
   #                        dropMessage='Drop you file here or double click this area',
   #                        importButton_action="""
   #                                genro.publish('import_users',{filepath:imported_file_path})
   #                            """,
   #                        matchColumns='*',
   #                        importStructure=self.db.table('adm.user').importerStructure())
   #                        
   #    bar.dataRpc(self.db.table('adm.user').importUserFromFile,
   #                    subscribe_import_users=True,
   #                    _lockScreen=dict(thermo=True),
   #                    _onResult="""
   #                                genro.publish('importUsers_onResult',result);
   #                                """)
   #                            # _onError="""
   #                            # genro.bp(true);
   #                            #     genro.publish('importRigheListino_onResult',{error:error});
   #                            # """)
        
    def th_order(self):
        return 'username'
        
    def th_query(self):
        return dict(column='username',op='contains', val='')


class ViewPicker(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('username',name='Username',width='15em')
        r.fieldcell('group_code',name='Group',width='10em')

class Form(BaseComponent):
    
    #def th_form(self, form):
    #    pane = form.record
    #    pane.div('!!Login Data', _class='pbl_roundedGroupLabel')
    #    fb = pane.div(margin='5px').formbuilder(cols=2, border_spacing='6px',width='100%',fld_width='100%')
    #    fb.field('firstname',lbl='!!Firstname')
    #    fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Existing')
    #    fb.field('lastname',lbl='!!Lastname')
    #    fb.textBox(value='^.md5pwd', lbl='Password', type='password',validate_notnull=True, validate_notnull_error='!!Required')
    #    fb.field('status', tag='filteringSelect', values='!!conf:Confirmed,wait:Waiting', 
    #             validate_notnull=True, validate_notnull_error='!!Required')
    #    fb.field('group_code')
    #    fb.field('email', lbl='!!Email')
    
    def th_form(self,form,**kwargs):
        bc = form.center.borderContainer()
        self.loginData(bc.roundedGroup(title='Login',region='top',datapath='.record',height='200px'))
        self.adm_user_maintc(bc.tabContainer(region='center',margin='2px'))

        
        
    def loginData(self,pane):
        fb = pane.div(margin_right='10px').formbuilder(cols=2, border_spacing='4px',colswidth='12em')
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')

        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists')
        fb.textBox(value='^.md5pwd', lbl='Password', type='password',validate_notnull=True, validate_notnull_error='!!Required')
        
        fb.field('status', tag='filteringSelect', # values='!!conf:Confirmed,wait:Waiting', 
                 validate_notnull=True, validate_notnull_error='!!Required')
        fb.field('group_code')
        fb.field('locale', lbl='!!Locale')
        fb.field('avatar_rootpage',lbl='!!Startpage',tip='!!User start page')
        fb.field('email', lbl='!!Email',colspan=2,width='100%')
        fb.field('sms_login', html_label=True)
        fb.field('sms_number',hidden='^.sms_login?=!#v',colspan=2,width='100%')
        
    @customizable
    def adm_user_maintc(self,tc):
        self.userAuth(tc.contentPane(title='Auth'))
        self.userConfigView(tc.contentPane(title='Config'))
        
    def th_form(self,form,**kwargs):
        bc = form.center.borderContainer()
        self.loginData(bc.roundedGroup(title='Login',region='top',datapath='.record',height='200px'))
        self.adm_user_maintc(bc.tabContainer(region='center',margin='2px'))

    def userAuth(self,pane):
        pane.inlineTableHandler(relation='@tags',viewResource='ViewFromUser',
                            pbl_classes=True,margin='2px',addrow=True,picker='tag_id',
                            picker_condition='$child_count=0',
                            picker_viewResource=True)

    def userConfigView(self,pane):
        pane.dialogTableHandler(table='adm.user_config',margin='2px',
                                viewResource='ViewFromUser',
                                formResource='FormFromUser')
        

class ExtUserForm(BaseComponent):
    def th_form(self, form):
        fb = form.record.div(margin='5px',margin_right='15px').formbuilder(width='100%',
                            fld_width='100%',colswidth='auto')
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Existing')
        fb.textBox(value='^.md5pwd', lbl='Password', 
                    type='password',validate_notnull=True, 
                    validate_notnull_error='!!Required')
        fb.field('group_code',hasDownArrow=True)
        fb.field('email', lbl='!!Email')

    def th_options(self):
        return dict(modal=True,height='150px',width='380px')

class ExtUserView(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('username',name='!!Username',width='10em')
        r.fieldcell('group_code',name='!!Group',width='10em')
        r.fieldcell('email',name='!!Email',width='20em')
        #r.fieldcell('all_tags',name='!!Tags',width='15em')
        
    def th_order(self):
        return 'username'



class FormProfile(BaseComponent):

    def th_options(self):
        return dict(showtoolbar=False)
        
    def th_form(self,form):
        bc = form.center.borderContainer()
        fb = bc.contentPane(region='top',datapath='.record',margin_top='10px').formbuilder(cols=4, 
                        border_spacing='4px',colswidth='auto',width='100%',fld_width='100%')
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')
        fb.div()
        fb.img(src='^.photo',crop_height='100px',crop_width='100px',margin_left='25px',
                    crop_border='2px dotted silver',crop_rounded=6,edit=True,
                    placeholder=True,upload_folder='*',takePicture=True,rowspan=4)
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists',readOnly=True)
        fb.field('locale', lbl='!!Locale',tag='combobox',values='en_En:')
        fb.br()
        fb.field('email', lbl='!!Email',colspan=2,width='100%')
        #
        #fb.field('sms_login', html_label=True)
        #fb.field('sms_number',hidden='^.sms_login?=!#v',colspan=2,width='12em')
        tc = bc.tabContainer(margin='2px',region='center')
        self.adm_profile_tabs(tc)
    
    @customizable
    def adm_profile_tabs(self,tc):
        self.authenticationsPane(tc.borderContainer(title='!!Authentication'))
        frame_preference = tc.framePane(title='!![en]Preferences',margin='2px',border='1px solid silver',rounded=6)
        frame_preference.top.slotToolbar('*,stackButtons,*')
        frame_preference.center.userPreferencesTabs(datapath='#FORM.record.preferences',margin='2px',region='center',wdg='stack')

    @customizable
    def authenticationsPane(self,bc):
        pane = bc.contentPane(region='top')
        fb = pane.formbuilder(datapath='#FORM.record')
        fb.button('!!Change password',action="genro.mainGenroWindow.genro.publish('openNewPwd')")
        if pyotp:
            button = fb.button('Enable 2fa')
            fb.div('^#FORM.record.last_2fa_otp',lbl='2fa ENABLED',hidden='^#FORM.enabled_2fa?=!#v')
            rpc = button.dataRpc('#FORM.2fa_enabler.2fa_data',self.get2faData)
            rpc.addCallback('dlg.show()',dlg=self._dlg2faQrcode(fb).js_widget)
            dlg = pane.dialog(title='Enabling 2fa',closable=True,datapath='#FORM.2fa_enabler')
            frame = dlg.framePane(height='300px',width='400px')
            frame.center.contentPane().img(src='^.2fa_data.previsioning_uri?="/_tools/qrcode/"+#v',height='100%',width='100%')
        return bc
    
    def _dlg2faQrcode(self,pane):
        dlg = pane.dialog(title='Enabling 2fa',closable=True,datapath='#FORM.2fa_enabler')
        frame = dlg.framePane(height='300px',width='300px')
        frame.center.contentPane(overflow='hidden').img(src='^#FORM.2fa_enabler.2fa_data.qrcode_url',
                                                        height='100%',margin='auto')
        frame.bottom.div('^#FORM.2fa_enabler.2fa_data.previsioning_uri',height='30px',_class='selectable')
        fb = frame.bottom.formbuilder()
        fb.textbox(value='^.otp',lbl='OTP')
        bar = frame.bottom.slotBar('*,confirm,5',childname='confirmbar',height='22px',border='1px solid silver')
        rpc = bar.slotButton('Confirm').dataRpc(
            self.confirmOTP,otp='=.otp'
        )
        rpc.addCallback("""if(result){
            dlg.hide(); 
            SET #FORM.2fa_enabler.2fa_data = null;
            SET #FORM.record.avatar_enabled_2fa = true;
            SET #FORM.record.avatar_last_2fa_otp = otp;
            this.form.save();
        }
        """,dlg=dlg.js_widget,otp='=.otp')
        return dlg

    @public_method
    def get2faData(self):
        result = Bag()
        service = self.getService('2fa')
        previsioning_uri = service.getPrevisioningUri(self.user,user_id=self.avatar.user_id)
        result['secret'] = str(service.get2faSecret(self.avatar.user_id))
        result['previsioning_uri'] = previsioning_uri
        result['qrcode_url'] =f'/_tools/qrcode?{urllib.parse.urlencode({"url":previsioning_uri})}' 
        return result

    @public_method
    def confirmOTP(self,otp=None):
        result = self.getService('2fa').verifyTOTP(self.avatar.user_id,otp=otp)
        return result