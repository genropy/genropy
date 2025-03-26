# -*- coding: utf-8 -*-

# th_user.py
# Created by Saverio Porcari on 2011-03-13.
# Copyright (c) 2011 Softwell. All rights reserved.

import urllib
import json

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method,customizable
from gnr.core.gnrbag import Bag

from gnr.core.gnrlang import getUuid

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

class FormFromUserInfo(BaseComponent):

    def th_form(self,form):
        fl = form.record.formlet(cols=2)
        fl.field('firstname')
        photo_size = '100px' if self.isMobile else '150px'
        fl.img(src='^.photo',crop_height=photo_size,crop_width=photo_size,box_width=photo_size,
                    crop_border='2px dotted silver',crop_rounded=6,edit=True,
                    placeholder=True,upload_folder='*',takePicture=True,rowspan=4,lbl='!![en]Photo')
        fl.field('lastname')
        fl.field('language')
        fl.field('locale',tag='comboBox',values='en_EN:English,en_US:USA,it_IT:Italian')
        fl.field('email',colspan=2)

    def th_options_autoSave(self):
        return True

    def th_options_showtoolbar(self):
        return False

class FormFrom2FaSettings(BaseComponent):

    def th_options_showtoolbar(self):
        return False


    def th_form(self, form):
        pane = form.record
        with open(self.getResource('localized_texts.json',pkg='adm'), 'r', encoding='utf-8') as f:
            content_dict = json.loads(f.read())['two_factor_auth']
        text = content_dict.get(self.language.lower()) or content_dict['en']
        pane.div(text,padding_left='10px',padding_right='10px')

        flexbox = pane.flexbox(flex_direction='row-reverse',padding='10px')

        flexbox.button('Enable', margin_top='5px',padding_top='1px',padding_bottom='1px',
                            hidden='^#FORM.record.avatar_secret_2fa'
                                ).dataController(
                                        """dlg.setRelativeData('.secret',avatar_secret_2fa  || genro.time36Id());
                                            dlg.widget.show()
                                        """,
                                dlg=self._dlg2faQrcode(pane),
                                avatar_secret_2fa='=FORM.record.avatar_secret_2fa')
        flexbox.button('Disable', margin_top='5px',padding_top='1px',padding_bottom='1px',
                                hidden='^#FORM.record.avatar_secret_2fa?=!#v'
                                ).dataController(
                                        """SET #FORM.record.avatar_secret_2fa=null;""")
        
    
    def _dlg2faQrcode(self,pane):
        dlg = pane.dialog(title='Enabling 2fa',closable=True,datapath='#FORM.2fa_enabler')
        frame = dlg.framePane(height='300px',width='300px')
        fb = frame.top.formbuilder(cols=1)
        fb.textbox(value='^.secret',lbl='Secret',placeholder='Autogenerated secret',
                   disabled='^#FORM.record.avatar_secret_2fa')
        fb.dataRpc('#FORM.2fa_enabler.2fa_data',self.get2faData,secret='^.secret')
        frame.center.contentPane(overflow='hidden'
                                 ).div(height='200px',width='200px',margin='auto').img(src='^#FORM.2fa_enabler.2fa_data.qrcode_url',
                                                        height='100%')
        bottom = frame.bottom.div(height='50px')
        bottom.lightbutton('Copy code to clipboard',text_align='center',cursor='pointer',
                           font_size='.9em',font_weight='bold',color='#444',
                      action="genro.textToClipboard(secret,'Copied')",
                      secret='^#FORM.2fa_enabler.2fa_data.secret')       
        fb = bottom.formbuilder()
        fb.textbox(value='^.otp',lbl='OTP')
        bar = frame.bottom.slotBar('*,confirm,5',childname='confirmbar',height='22px',border='1px solid silver')
        rpc = bar.slotButton('Add').dataRpc(
            self.confirmOTP,otp='=.otp',
            user_id='=#FORM.record.id',
            secret='=.secret'
        )
        rpc.addCallback("""if(result){
                dlg.hide(); 
                SET #FORM.2fa_enabler.2fa_data = null;
                this.form.reload();
            }else{
                genro.dlg.alert('Wrong otp')
            }
        """,dlg=dlg.js_widget,otp='=.otp')
        return dlg

    @public_method
    def get2faData(self,secret=None):
        secret = secret or getUuid()
        result = Bag()
        service = self.getService('2fa')
        secret = secret or getUuid()
        previsioning_uri = service.getPrevisioningUri(name=self.user,secret=secret)
        result['secret'] = str(service.get2faSecret(secret))
        result['previsioning_uri'] = previsioning_uri
        result['qrcode_url'] =f'/_tools/qrcode?{urllib.parse.urlencode({"url":previsioning_uri})}' 
        self.db.commit()
        return result

    @public_method
    def confirmOTP(self,user_id=None,otp=None,secret=None):
        result = self.getService('2fa').verifyTOTP(secret=secret,otp=otp)
        if result:
            with self.db.table('adm.user').recordToUpdate(user_id) as user:
                user['avatar_last_2fa_otp'] = otp
                user['avatar_secret_2fa'] = secret
            self.db.commit()
        return result
    


class FormUserSettings(BaseComponent):
    py_requires ='gnrcomponents/settingmanager/settingmanager:SettingManager AS setting_manager'
    def th_form(self,form):
        self.setting_manager.setting_panel(form.center.contentPane(),title='!![en]User settings',
                                            table='adm.user_setting',datapath='.setting_manager',
                                            frameCode='user_settings',
                                            storepath='#FORM.record.preferences')

        form.dataController("""
                                if(_subscription_kwargs.setting_path){
                                    let treeNode = genro.nodeById('V_user_settings_tree');
                                    treeNode.widget.setSelectedPath(null,{value:_subscription_kwargs.setting_path});  
                                    setTimeout(function(){
                                        treeNode.fireEvent('#ANCHOR.formlets.load',true);
                                    },100)  
                                    
                                }    
                               """,
                            subscribe_user_setting_open=True
                            )

    def th_options_showtoolbar(self):
        return False

    def th_options_autoSave(self):
        return True


class Form(BaseComponent):
    py_requires="login:LoginComponent"

    def th_form(self,form,**kwargs):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top',datapath='.record',height='240px')
        self.loginData(top.roundedGroup(title='!!User info', region='center'))
        self.loginFields(top.roundedGroup(title='!!Login info', region='right', width='400px'))
        self.adm_user_maintc(bc.tabContainer(region='center',margin='2px'))
        
    def loginData(self,pane):
        fb = pane.div(margin_right='10px').formbuilder(cols=2, border_spacing='4px',colswidth='12em')
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')
        fb.field('status', tag='filteringSelect', # values='!!conf:Confirmed,wait:Waiting', 
                 validate_notnull=True, validate_notnull_error='!!Required')
        fb.field('locale', lbl='!!Locale')
        fb.field('language', lbl='!![en]Language')
        fb.field('group_code',lbl='!![en]Main group',hasDownArrow=True)
        fb.checkBoxText('^._other_groups',lbl='!![en]Other groups',
                        table='adm.group',
                        _virtual_column='other_groups',popup=True)
        fb.field('avatar_rootpage',lbl='!!Startpage',tip='!!User start page',colspan=2,width='100%')
        fb.field('email', lbl='!!Email',colspan=2,width='100%')
        fb.field('sms_login', html_label=True)
        fb.field('sms_number',hidden='^.sms_login?=!#v',colspan=2,width='100%')

    def loginFields(self, pane):
        fb = pane.div(margin_right='10px').formbuilder(cols=1, border_spacing='4px',colswidth='12em')
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists')
        fb.passwordTextBox(value='^.md5pwd', lbl='Password',validate_notnull=True, validate_notnull_error='!!Required')
        fb.button('!!Reset password').dataRpc(self.login_confirmNewPassword, 
                                                username='=.username', email='=.email')
        
    @customizable
    def adm_user_maintc(self,tc):
        self.userAuth(tc.contentPane(title='!!Auth'))
        self.userConfigView(tc.contentPane(title='!!Config'))

    def userAuth(self,pane):
        pane.inlineTableHandler(relation='@tags',viewResource='ViewFromUser',
                            pbl_classes=True,margin='2px',addrow=True,picker='tag_id',
                            picker_condition='$child_count=0',
                            picker_viewResource=True)

    def userConfigView(self,pane):
        pane.dialogTableHandler(table='adm.user_config',margin='2px',
                                viewResource='ViewFromUser',
                                formResource='FormFromUser')
        

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        if not newrecord:
            other_groups= record['other_groups']
            record.setItem('_other_groups',other_groups,_sendback=True)


    @public_method
    def th_onSaving(self,recordCluster,recordClusterAttr=None,resultAttr=None,**kwargs):
        other_groups = recordCluster.pop('_other_groups')
        return dict(other_groups=other_groups)

    @public_method
    def th_onSaved(self, record, resultAttr,other_groups=None,**kwargs):
        user_group = self.db.table('adm.user_group')
        user_id = record['id']
        user_group.deleteSelection(where='$user_id=:uid',uid=user_id)
        if other_groups:
            for gr in other_groups.split(','):
                user_group.insert(user_group.newrecord(user_id=user_id,group_code=gr))


class PublicForm(BaseComponent):

    def th_form(self,form,**kwargs):
        pane = form.record
        self.loginData(pane)

    def loginData(self,pane):
        fb = pane.mobileFormBuilder(cols=1)
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')
        fb.field('email', lbl='!!Email')
        

class ExtUserForm(BaseComponent):
    def th_form(self, form):
        fb = form.record.div(margin='5px',margin_right='15px').formbuilder(width='100%',
                            fld_width='100%',colswidth='auto')
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Existing')
        fb.passwordTextBox(value='^.md5pwd', lbl='Password', 
                            validate_notnull=True, validate_notnull_error='!!Required')
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


class FormSimple(BaseComponent):

    def th_options(self):
        return dict(modal=True,dialog_height='200px',dialog_width='300px')
        
    def th_form(self,form):
        bc = form.center.borderContainer()
        fb = bc.contentPane(region='top',datapath='.record',margin_top='10px').mobileFormBuilder(cols=1)
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists')
        fb.passwordTextBox(value='^.md5pwd', lbl='Password', validate_notnull=True, validate_notnull_error='!!Required')
        fb.field('status')
        fb.field('email', lbl='!!Email')


class FormProfile(BaseComponent):
        
    def th_form(self,form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top',datapath='.record',margin_top='10px', height='170px' if self.isMobile else '130px')
        
        fb = top.contentPane(region='center').formlet(cols=1 if self.isMobile else 2)
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists',protected=True)
        fb.field('email', lbl='!!Email')
        
        right = top.contentPane(region='right', width='104px', margin='10px 25px')
        right.img(src='^.photo',crop_height='100px',crop_width='100px',
                    crop_border='2px dotted silver',crop_rounded=6,edit=True,
                    placeholder=True,upload_folder='*',takePicture=True,rowspan=4)
        
        self.adm_profile_tabs(bc.tabContainer(margin='2px',region='center'))
    
    def th_options(self):
        return dict(showtoolbar=False)
    
    @customizable
    def adm_profile_tabs(self,tc):
        self.authenticationsPane(tc.contentPane(title='!!Authentication'))
        frame_preference = tc.framePane(title='!![en]Preferences',margin='2px',border='1px solid silver',rounded=6)
        frame_preference.top.slotToolbar('*,stackButtons,*',_class='mobile_bar')
        frame_preference.center.userPreferencesTabs(datapath='#FORM.record.preferences',margin='2px',region='center',wdg='stack')

    @customizable
    def authenticationsPane(self,pane):
        pane.div('!![en]Password', _class='preference_subtitle')
        fb = pane.formbuilder(datapath='#FORM.record')
        fb.button('!!Change password',action="genro.mainGenroWindow.genro.publish('openNewPwd')")
    
    

class FormProfileMobile(FormProfile):

    def th_form(self,form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top',datapath='.record',margin_top='10px', height='170px')
        
        fb = top.contentPane(region='center').mobileFormBuilder(cols=1)
        fb.field('firstname',lbl='!!Firstname')
        fb.field('lastname',lbl='!!Lastname')
        fb.field('username',lbl='!!Username',validate_nodup=True,validate_notnull_error='!!Exists',protected=True)
        fb.field('email', lbl='!!Email')
        
        right = top.contentPane(region='right', width='104px', margin='10px 25px')
        right.img(src='^.photo',crop_height='100px',crop_width='100px',
                    crop_border='2px dotted silver',crop_rounded=6,edit=True,
                    placeholder=True,upload_folder='*',takePicture=True,rowspan=4)
        
        self.adm_profile_tabs(bc.tabContainer(margin='2px',region='center'))