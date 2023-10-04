# -*- coding: utf-8 -*-

# th_user.py
# Created by Saverio Porcari on 2011-03-13.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method,customizable
from gnr.core.gnrbag import Bag
import urllib
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

class Form(BaseComponent):
    
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
        fb.field('locale', lbl='!!Locale')

        fb.field('group_code',lbl='!![en]Main group',hasDownArrow=True)
        fb.checkBoxText('^._other_groups',lbl='!![en]Other groups',
                        hidden='^.group_code?=!#v',
                        table='adm.group',condition='$code!=:maingroup',
                        condition_maingroup='^.group_code',
                        _virtual_column='other_groups',popup=True)
        fb.field('avatar_rootpage',lbl='!!Startpage',tip='!!User start page',colspan=2,width='100%')
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
        self.authenticationsPane(tc.contentPane(title='!!Authentication'))
        frame_preference = tc.framePane(title='!![en]Preferences',margin='2px',border='1px solid silver',rounded=6)
        frame_preference.top.slotToolbar('*,stackButtons,*')
        frame_preference.center.userPreferencesTabs(datapath='#FORM.record.preferences',margin='2px',region='center',wdg='stack')

    @customizable
    def authenticationsPane(self,pane):
        fb = pane.formbuilder(datapath='#FORM.record')
        fb.button('!!Change password',action="genro.mainGenroWindow.genro.publish('openNewPwd')")
        if self.getService('2fa'):
            button = fb.button('Enable 2fa')
            button.dataController("""dlg.setRelativeData('.secret',avatar_secret_2fa  || genro.time36Id());
                                    dlg.widget.show()
                                    """,
                                  dlg=self._dlg2faQrcode(fb),
                                  avatar_secret_2fa='=FORM.record.avatar_secret_2fa')
            fb.div('^#FORM.record.last_2fa_otp',lbl='2fa ENABLED',hidden='^#FORM.enabled_2fa?=!#v')
            fb.div('^#FORM.record.avatar_secret_2fa?=#v?"2FA enabled":"2FA not enabled"')
            dlg = pane.dialog(title='Enabling 2fa',closable=True,datapath='#FORM.2fa_enabler')
            frame = dlg.framePane(height='300px',width='400px')
            frame.center.contentPane().img(src='^.2fa_data.previsioning_uri?="/_tools/qrcode/"+#v',height='100%',width='100%')
        return fb
    
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