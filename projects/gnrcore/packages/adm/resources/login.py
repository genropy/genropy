# -*- coding: utf-8 -*-

# frameindex.py
# Created by Francesco Porcari on 2011-04-06.
# Copyright (c) 2011 Softwell. All rights reserved.
# Frameindex component

from builtins import str
from gnr.web.gnrwebpage import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwebstruct import struct_method
from datetime import date
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrRestrictedAccessException
from gnr.core.gnrdecorator import customizable
        
class LoginComponent(BaseComponent):
    css_requires = 'login'
    js_requires = 'login'
    login_error_msg = '!!Invalid login'
    new_window_title = '!!New Window'
    auth_workdate = 'admin'
    auth_page = 'user'
    login_splash_url = None
    closable_login = False
    loginBox_kwargs = dict()
    external_verified_user = None
    
    @customizable
    def loginDialog(self,pane,gnrtoken=None,closable_login=None,**kwargs):
        closable_login = self.closable_login if closable_login is None else closable_login
        doLogin = self.avatar is None and self.auth_page
        if doLogin and not closable_login and self.login_splash_url:
            pane.css('.dijitDialogUnderlay.lightboxDialog_underlay',"opacity:0;")
            if self.login_splash_url:
                pane.iframe(height='100%', width='100%', src=self.getResourceUri(self.login_splash_url), border='0px') 
        loginKwargs = dict(_class='lightboxDialog loginDialog' if self.loginPreference('login_flat') else 'lightboxDialog') 
        loginKwargs.update(self.loginBox_kwargs)

        dlg = pane.dialog(subscribe_openLogin="this.widget.show()",
                          subscribe_closeLogin="this.widget.hide()",**loginKwargs)
        box = dlg.div(**self.loginboxPars())
        if closable_login:
            dlg.div(_class='dlg_closebtn',connect_onclick='PUBLISH closeLogin;')
        login_title = self.loginPreference('login_title')
        new_window_title = self.loginPreference('new_window_title')

       #login_title = login_title or '!!Login'
       #new_window_title = new_window_title or '!!New Window'
        wtitle =  login_title if doLogin else new_window_title
        self.login_commonHeader(box,title=wtitle,subtitle=self.loginPreference('login_subtitle'))
        self.loginDialog_center(box,doLogin=doLogin,gnrtoken=gnrtoken,dlg=dlg,closable_login=closable_login)
        footer = self.login_commonFooter(box)
        self.loginDialog_bottom_left(footer.leftbox,dlg)
        self.loginDialog_bottom_right(footer.rightbox,dlg)
        self.callPackageHooks('loginExtra',box)
        return box

    def login_commonFooter(self,pane):
        return pane.slotBar('15,leftbox,*,rightbox,15',height='45px')


    def login_commonHeader(self,pane,title=None,subtitle=None):
        pane = pane.div(margin_top='10px')
        pane.div(text_align='center').cover_logo(height='30px')
        if title:
            pane.div(title,_class='index_logintitle')
        if subtitle:
            pane.div(subtitle,_class='index_loginsubtitle')

    def loginDialog_bottom_left(self,pane,dlg):
        if self.loginPreference('forgot_password'):
            pane.lightbutton('!!Lost password',action='FIRE lost_password_dlg;',
                            _class='login_option_btn')
            pane.dataController("dlg_login.hide();dlg_lp.show();",_fired='^lost_password_dlg',
            dlg_login=dlg.js_widget,dlg_lp=self.login_lostPassword(pane,dlg).js_widget)
        if self.loginPreference('new_user'):
            self.login_newUser(pane)
            pane.lightbutton('!!New User',action='genro.publish("closeLogin");genro.publish("openNewUser");',
                            _class='login_option_btn')

    def loginDialog_bottom_right(self,pane,dlg):
        pane.button('!!Enter',action='FIRE do_login_check',_class='login_confirm_btn')

    def loginDialog_center(self,pane,doLogin=None,gnrtoken=None,dlg=None,closable_login=None):
        fb = pane.div(_class='login_form_container').htmlform().formbuilder(cols=1, border_spacing='4px',onEnter='FIRE do_login_check;',
                                datapath='gnr.rootenv',width='100%',
                                fld_width='100%',row_height='3ex',keeplabel=True
                                ,fld_attr_editable=True)
        rpcmethod = self.login_newWindow
        start = 0
        if doLogin:
            start = 3
            tbuser = fb.textbox(value='^_login.user',lbl='!!Username',row_hidden=False,
                                nodeId='tb_login_user',autocomplete='username',disabled=self.external_verified_user,
                                validate_onAccept="""genro.publish('onUserEntered',{username:value})""")
            tbpwd = fb.PasswordTextBox(value='^_login.password',lbl='!!Password',row_hidden=self.external_verified_user,
                                    nodeId='tb_login_pwd',autocomplete='current-password')
            fb.dbSelect(value='^_login.group_code',table='adm.group',
                        condition="""$code IN :all_groups 
                                    AND (:secret_2fa IS NOT NULL OR $require_2fa IS NOT TRUE)""",
                        condition_secret_2fa='=gnr.avatar.secret_2fa',
                    condition_all_groups='^.all_groups',validate_notnull='^.group_selector',
                    row_hidden='^.group_selector?=!#v',lbl='!![en]Group',hasDownArrow=True,
                    validate_onAccept="""
                    if(userChange){
                        let avatar_group_code = GET gnr.avatar.group_code;
                        if(avatar_group_code!=value){
                            FIRE _login.checkAvatar;
                        }
                    }
                    """
                    )
            fb.dataController("""
                SET _login.password = null;
                SET _login.group_code = null;  
                SET gnr.avatar = null;
            """,
                _changed_user='^_login.user',_userChanges=True
            )
            fb.dataController("""if(user && pwd){
                FIRE do_login;
            }else{
                user = user || tbuser.widget.getValue();
                pwd = pwd || tbpwd.widget.getValue() || external_verified_user;
                PUT _login.user = user;
                PUT _login.password = pwd;
                FIRE _login.checkAvatar;
            }
            
            """,_fired='^do_login_check',user='=_login.user',avatar_user='=gnr.avatar.user',
                        tbuser=tbuser,tbpwd=tbpwd,external_verified_user=self.external_verified_user,
                        pwd='=_login.password')

            pane.dataRpc(self.login_checkAvatar,
                        user='^_login.user',
                        password='^_login.password',
                        group_code='=_login.group_code',
                        _fired='^_login.checkAvatar',
                        _onCalling="""
                        SET gnr.avatar = null;
                        kwargs.serverTimeDelta = genro.serverTimeDelta;
                        """,
                        _if='user&&password',
                        _fb = fb,
                        _onResult="""LoginComponent.onCheckAvatar(kwargs._fb,result)""",
                        sync=True,_POST=True,
                        _userChanges=True)
            rpcmethod = self.login_doLogin    
        else:
            fb.dataController("""FIRE do_login;""",_fired='^do_login_check')
        
        fb.dateTextBox(value='^.workdate',lbl='!!Workdate')
        valid_token = False
        if gnrtoken:
            valid_token = self.db.table('sys.external_token').check_token(gnrtoken)
        self.callPackageHooks('rootenvForm',fb)
        for fbnode in fb.getNodes()[start:]:
            if fbnode.attr['tag']=='tr':
                fbnode.attr['hidden'] = '==!_avatar || _hide '
                fbnode.attr['_avatar'] = '^gnr.avatar.user'
                fbnode.attr['_hide'] = '%s?hidden' %fbnode.value['#1.#0?value']
        if gnrtoken or not closable_login:
            pane.dataController("""
                            var href = window.location.href;
                            if(window.location.search){
                                var urlParsed = parseURL(window.location.href);
                                objectExtract(urlParsed.params,'gnrtoken,new_window,custom_index');        
                                window.history.replaceState({},document.title,serializeURL(urlParsed));

                            }
                            if(new_password){
                                if(valid_token){
                                    newPasswordDialog.show();
                                }else{

                                    PUBLISH openLogin;
                                    setTimeout(function(){
                                            genro.publish('failed_login_msg',{message:invalid_token_message});
                                        },1000);
                                }
                                
                            }else{
                                PUBLISH openLogin;
                            }
                            
                            """,_onBuilt=True,
                            new_password=gnrtoken or False,loginDialog = dlg.js_widget,
                            valid_token = valid_token,invalid_token_message='!!Change password link expired',
                            newPasswordDialog = self.login_newPassword(pane,gnrtoken=gnrtoken,dlg_login=dlg).js_widget,
                            fb=fb)


        dlg.dataController("genro.dlg.floatingMessage(sn,{message:message,messageType:'error',yRatio:1.85})",subscribe_failed_login_msg=True,sn=dlg)

        pane.dataController("dlg_login.hide();dlg_cu.show();",dlg_login=dlg.js_widget,
                    dlg_cu=self.login_confirmUserDialog(pane,dlg).js_widget,subscribe_confirmUserDialog=True)

        pane.dataController("dlg_login.hide();dlg_otp.show();",dlg_login=dlg.js_widget,
                    dlg_otp=self.login_otpDialog(pane,dlg).js_widget,subscribe_getOtpDialog=True)

        pane.dataController("""
            LoginComponent.confirmAvatar(fb,rpcmethod,dlg,doLogin,error_msg,standAlonePage)
        """,fb=fb,
            _fired='^do_login',
            rpcmethod=rpcmethod,
            standAlonePage=self.pageOptions.get('standAlonePage'),
            error_msg='!!Invalid login',
            dlg=dlg.js_widget,
            doLogin=doLogin,
            _delay=1)  
        return dlg
        

    @public_method
    def login_doLogin(self, rootenv=None,login=None,guestName=None, **kwargs):
        waiting2fa = self.pageStore().getItem('waiting2fa')
        if waiting2fa:
            return {'error':'Waiting authentication code'}
        kwargs.pop('authenticate',None)
        self.doLogin(login=login,guestName=guestName,rootenv=rootenv,**kwargs)
        if login['error']:
            return dict(error=login['error'])
        rootenv['user'] = self.avatar.user
        rootenv['user_id'] = self.avatar.user_id
        rootenv['user_group_code'] = getattr(self.avatar,'group_code',None)
        rootenv['workdate'] = rootenv['workdate'] or self.workdate
        rootenv['login_date'] = date.today()
        rootenv['language'] = rootenv['language'] or self.language
        self.connectionStore().setItem('defaultRootenv',rootenv) #no need to be locked because it's just one set
        return self.login_newWindow(rootenv=rootenv)

    @public_method
    def login_checkAvatar(self,password=None,user=None,group_code=None,serverTimeDelta=None,**kwargs):
        result = Bag()
        try:
            avatar = self.application.getAvatar(user, password=password,group_code=group_code,authenticate=True)
            if not avatar:
                return result
        except GnrRestrictedAccessException as e:
            return Bag(login_error_msg=e.description)
        status = getattr(avatar,'status',None)
        if not status:
            avatar.extra_kwargs['status'] = 'conf'
        result['avatar'] = Bag(avatar.as_dict())
        if avatar.status != 'conf':
            return result
        self.login_completeRootEnv(result,avatar=avatar,serverTimeDelta=serverTimeDelta)
        if self.login_require2fa(avatar):
            result['waiting2fa'] = avatar.user_id
            with self.pageStore() as ps:
                ps.setItem('waiting2fa',avatar.user_id)
                ps.setItem('last_2fa_otp',avatar.last_2fa_otp)
        return result
    
    def login_require2fa(self,avatar):
        service = self.getService('2fa')
        if not service:
            return False
        enabled = avatar.extra_kwargs.get('secret_2fa') 
        return enabled and not self.getService('2fa').saved2fa(avatar.user_id)
    
    def login_completeRootEnv(self,result,avatar=None,serverTimeDelta=None):
        data = Bag()
        data['serverTimeDelta'] = serverTimeDelta
        data['group_selector'] = False
        if avatar.extra_kwargs.get('main_group_code'):
            other_groups = self.db.table('adm.user_group').query(where='$user_id=:uid',uid=avatar.user_id).fetch()
            data['all_groups'] = [avatar.main_group_code]
            if other_groups:
                data['all_groups'] = [avatar.main_group_code] + [g['group_code'] for g in other_groups]
                data['group_selector'] = True
        self.callPackageHooks('onUserSelected',avatar,data)
        canBeChanged = self.application.checkResourcePermission(self.pageAuthTags(method='workdate'),avatar.user_tags)
        default_workdate = self.clientDatetime(serverTimeDelta=serverTimeDelta).date()
        data.setItem('workdate',default_workdate, hidden= not canBeChanged)
        result['rootenv'] = data
        return result

    def loginboxPars(self):
        return dict(width='320px',_class='index_loginbox')

    def login_lostPassword(self,pane,dlg_login):
        dlg = pane.dialog(_class='lightboxDialog loginDialog')
        box = dlg.div(**self.loginboxPars())
        self.login_commonHeader(box,'!!Lost password')
        fb = box.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='4px',onEnter='FIRE recover_password;',
                                datapath='lost_password',width='100%',
                                fld_width='100%',row_height='3ex')
        fb.textbox(value='^.email',lbl='!!Email')
        fb.dataRpc(self.login_confirmNewPassword, _fired='^recover_password',_if='email',email='=.email',
                _onResult="""if(result=="ok"){
                    FIRE recover_password_ok;
                }else{
                    FIRE recover_password_err;
                }""")
        fb.dataController("""genro.dlg.floatingMessage(sn,{message:msg,messageType:'error',yRatio:.95})""",
                            msg='!!Missing user for this email',_fired='^recover_password_err',sn=dlg)
        fb.dataController("""genro.dlg.floatingMessage(sn,{message:msg,yRatio:.95})""",
                            msg='!!Check your email for instruction',_fired='^recover_password_ok',sn=dlg)
        footer = self.login_commonFooter(box)
        footer.leftbox.lightButton('!!Login',action='FIRE back_login;',_class='login_option_btn')
        footer.rightbox.button('!!Recover',action='FIRE recover_password',_class='login_confirm_btn')

        footer.dataController("dlg_lp.hide();dlg_login.show();",_fired='^back_login',
                        dlg_login=dlg_login.js_widget,dlg_lp=dlg.js_widget)
        return dlg

    def login_newPassword(self,pane,gnrtoken=None,dlg_login=None):
        dlg = pane.dialog(_class='lightboxDialog loginDialog',subscribe_closeNewPwd='this.widget.hide();',subscribe_openNewPwd='this.widget.show();')
        box = dlg.div(**self.loginboxPars())
        self.login_commonHeader(box,'!!New password')
        fb = box.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='4px',onEnter='FIRE set_new_password;',
                                datapath='new_password',width='100%',
                                fld_width='100%',row_height='3ex')
        if not gnrtoken:
            #change password by a logged user
            dlg.div(_class='dlg_closebtn',connect_onclick="genro.publish('closeNewPwd');")
            fb.passwordTextBox(value='^.current_password',lbl='!!Password')
        else:
            token_record = self.db.table('sys.external_token').record(id=gnrtoken, ignoreMissing=True).output('bag')
            record_user = self.db.table('adm.user').recordAs(token_record['parameters.userid'])
            if not record_user['username']:
                fb.textbox(value='^.newusername',lbl='!![en]Choose Username',
                           validate_notnull=True, validate_remote=self.login_checkNodupUsername)
            fb.data('.gnrtoken',gnrtoken)

        fb.passwordTextBox(value='^.password',lbl='!!New password',
                    validate_remote=self.db.table('adm.user').validateNewPassword)
        fb.passwordTextBox(value='^.password_confirm',lbl='!!Confirm password',
                    validate_call='return value==GET .password;',validate_call_message='!!Passwords must be equal')
        fb.dataRpc(self.login_changePassword,_fired='^set_new_password',
                    current_password='=.current_password',
                    newusername='=.newusername',
                    password='=.password',password_confirm='=.password_confirm',
                    _if='password==password_confirm',_box=box,
                    _else="genro.dlg.floatingMessage(_box,{message:'Passwords must be equal',messageType:'error',yRatio:.95})",
                    gnrtoken=gnrtoken,_onResult="""if(result){
                        genro.dlg.floatingMessage(kwargs._box,{message:'Wrong password',messageType:'error',yRatio:.95});
                        return;
                    }
                    genro.publish("closeNewPwd");genro.publish("openLogin")""")
        footer = self.login_commonFooter(box)
        footer.rightbox.button('!!Send',action='FIRE set_new_password',_class='login_confirm_btn')
        return dlg
    
    @public_method
    def login_checkNodupUsername(self,value=None,**kwargs):
        if not value:
            return Bag(dict(errorcode='Insert username'))
        if self.db.table('adm.user').checkDuplicate(username=value):
            return Bag(dict(errorcode=f'Existing username {value}'))
        return True
    def login_otpDialog(self,pane,dlg_login=None):
        dlg = pane.dialog(_class='lightboxDialog loginDialog',datapath='otp_prompt')
        box = dlg.div(**self.loginboxPars())
        self.login_commonHeader(box,'!![en]OTP Validation')
        box.div('!![en]Set the secure code from your authentication app',
                padding='10px 10px 0px 10px',
                color='#777',font_style='italic',
                font_size='.9em',text_align='center')
        fb = box.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='4px',onEnter='FIRE otp_confirm;',
                                datapath='new_password',width='100%',
                                fld_width='100%',row_height='3ex')
        fb.textbox(value='^.otp_code',lbl='!![en]Code',font_size='1.2em',font_weight='bold')
        fb.checkbox(value='^.otp_remember',label='!![en]Remember this client')
        footer = self.login_commonFooter(box)
        #footer.leftbox.lightButton('!!Login',action="genro.publish('closeNewUser');genro.publish('openLogin');",_class='login_option_btn')
        footer.rightbox.button('!![en]Confirm',_class='login_confirm_btn',action='FIRE otp_confirm')
        rpc = fb.dataRpc(self.login_checkOTPCode,
            _fired='^otp_confirm',
            otp_code='=.otp_code',
            otp_remember='=.otp_remember',
            _if='otp_code && otp_code.length==6',
            _else="genro.publish('failed_otp_msg',{'message':_msg});",
            _msg='!![en]Invalid code'
        )
        rpc.addCallback("""if(!result){
            genro.publish('failed_otp_msg',{'message':msg});
        }else{
            genro.setData('waiting2fa',false);
            dlg.hide();
            genro.publish('openLogin');
        }
        """,msg='!![en]Invalid code',dlg=dlg.js_widget)
        dlg.dataController("genro.dlg.floatingMessage(sn,{message:message,messageType:'error',yRatio:1.85})",subscribe_failed_otp_msg=True,sn=dlg)

        return dlg
    
    @public_method
    def login_checkOTPCode(self,otp_code=None,otp_remember=None):
        user_id = self.pageStore().getItem('waiting2fa')
        last_2fa_otp = self.pageStore().getItem('last_2fa_otp')
        if otp_code==last_2fa_otp:
            return False
        result = self.getService('2fa').verifyTOTP(user_id,otp=otp_code)
        if not result:
            return False
        with self.db.table('adm.user').recordToUpdate(user_id) as rec:
            rec['avatar_last_2fa_otp'] = otp_code
        self.db.commit()
        if otp_remember:
            self.getService('2fa').remember2fa(user_id)
        with self.pageStore() as ps:
            ps.setItem('waiting2fa',None)
            ps.setItem('last_2fa_otp',otp_code)
        return True



    def login_confirmUserDialog(self,pane,gnrtoken=None,dlg_login=None):
        dlg = pane.dialog(_class='lightboxDialog loginDialog')
        sc = dlg.stackContainer(**self.loginboxPars())
        box = sc.contentPane()
        confirmUserTitle = self.loginPreference('confirm_user_title') or '!!Confirm User'
        self.login_commonHeader(box,confirmUserTitle)
        self.login_commonHeader(sc.contentPane(),confirmUserTitle,self.loginPreference('check_email') or 'Please check your email')
        box.div(self.loginPreference('confirm_user_message'),padding='10px 10px 0px 10px',color='#777',font_style='italic',font_size='.9em',text_align='center')
        fb = box.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='4px',onEnter='FIRE confirm_email;',
                                datapath='new_password',width='100%',
                                fld_width='100%',row_height='3ex')
        fb.textbox(value='^.email',lbl='!!Email')
        fb.dataController("SET .email = avatar_email;",avatar_email='^gnr.avatar.email')
        fb.div(width='100%',position='relative',row_hidden=False).button('!!Send Email',action='FIRE confirm_email',position='absolute',right='-5px',top='8px')
        fb.dataRpc(self.login_confirmUser,_fired='^confirm_email',email='=.email',user_id='=gnr.avatar.user_id',
                    _if='email',
                    _onCalling='_sc.switchPage(1);',
                    _sc=sc.js_widget,
                    _else="genro.dlg.floatingMessage(_sn,{message:_error_msg,messageType:'error',yRatio:.95})",
                    _error_msg='!!Missing email',_sn=box)
        return dlg
        
        
    def login_newUser(self,pane,closable=False,**kwargs):
        dlg = pane.dialog(_class='lightboxDialog loginDialog',
                            subscribe_openNewUser='this.widget.show(); genro.formById("newUser_form").newrecord($1);',
                            subscribe_closeNewUser='this.widget.hide();')

        kw = self.loginboxPars()
        kw['width'] = '400px'
        kw['height'] = '280px'
        kw.update(kwargs)
        form = dlg.frameForm(frameCode='newUser',datapath='new_user',store='memory',**kw)
        if closable:
            dlg.div(_class='dlg_closebtn',connect_onclick="genro.publish('closeNewUser')")
        form.dataController("PUT creating_new_user = false;",_fired='^#FORM.controller.loaded')
        top = form.top
        self.login_commonHeader(top,'!!New User')
        self.login_newUser_form(form)
        form.dataRpc(self.login_createNewUser,data='=#FORM.record',
                    _do='^creating_new_user',_if='_do && this.form.isValid()',
                    _else='this.form.publish("message",{message:_error_message,messageType:"error"})',
                    _error_message='!!Missing data',
                    _onError="""
                    this.form.publish("message",{message:error,messageType:"error"});
                    PUT creating_new_user = false;
                    """,
                    _onResult="""if(result.ok){
                        genro.publish('closeNewUser');
                        genro.publish('floating_message',{message:result.ok,duration_out:6})
                    }
                    """,_lockScreen=True)
        footer = self.login_commonFooter(form.bottom)
        if not closable:
            footer.leftbox.lightButton('!!Login',action="genro.publish('closeNewUser');genro.publish('openLogin');",_class='login_option_btn')
        footer.rightbox.button('!!Send',action='SET creating_new_user = true;',_class='login_confirm_btn')
        return dlg

    def login_newUser_form(self,form):
        fb = form.record.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='6px',onEnter='SET creating_new_user = true;',
                                width='100%',tdl_width='6em',fld_width='100%',row_height='3ex')
        fb.textbox(value='^.firstname',lbl='!!First name',validate_notnull=True,validate_case='c',validate_len='2:')
        fb.textbox(value='^.lastname',lbl='!!Last name',validate_notnull=True,validate_case='c',validate_len='2:')
        fb.textbox(value='^.email',lbl='!!Email',validate_notnull=True)
        fb.textbox(value='^.username',lbl='!!Username',validate_notnull=True,validate_nodup='adm.user.username',validate_len='4:')

    @public_method
    def login_createNewUser(self,data=None,**kwargs):
        data['status'] = 'new'
        usertbl = self.db.table('adm.user')
        usertbl.insert(data)
        try:
            usertbl.sendInvitationEmail(user_record=data,async_=False,html=True,scheduler=False)
        except Exception as e:
            return  dict(error=str(e))
        self.db.commit()
        return dict(ok=self.loginPreference('new_user_ok_message') or 'Check your email to confirm')

    def loginPreference(self,path=None):
        if not hasattr(self,'_loginPreference'):
            self._loginPreference = self.db.table('adm.user').loginPreference()
        if not path:
            return self._loginPreference
        return self._loginPreference[path]
    
    @public_method
    def login_newWindow(self, rootenv=None, **kwargs): 
        errdict = self.callPackageHooks('onAuthenticating',self.avatar,rootenv=rootenv)
        result = self.avatar.as_dict()
        err = [err for err in errdict.values() if err is not None]
        with self.pageStore() as ps:
            rootenv['new_window_context'] = True
            ps.setItem('rootenv',rootenv)
        self.db.workdate = rootenv['workdate']
        self.setInClientData('gnr.rootenv', rootenv)
        if err:
            return {'error' : ', '.join(err)}
        return result

    @public_method
    def login_confirmUser(self, email=None,user_id=None, **kwargs):
        usertbl = self.db.table('adm.user')
        recordBag = usertbl.record(pkey=user_id,for_update=True).output('bag')
        userid = recordBag['id']
        oldrec = Bag(recordBag)
        recordBag['email'] = email
        recordBag['status'] = 'wait'
        usertbl.update(recordBag,oldrec)
        recordBag['link'] = self.externalUrlToken(self.site.homepage, userid=userid,max_usages=1)
        recordBag['greetings'] = recordBag['firstname'] or recordBag['lastname']
        tpl_userconfirm_id = self.loginPreference('tpl_userconfirm_id')
        mailservice = self.getService('mail')
        if tpl_userconfirm_id:
            mailservice.sendUserTemplateMail(record_id=recordBag,template_id=tpl_userconfirm_id,
                                             async_=False,html=True,scheduler=False)
        else:
            body = self.loginPreference('confirm_user_tpl') or 'Dear $greetings to confirm click $link'
            mailservice.sendmail_template(recordBag,to_address=email,
                                    body=body, subject=self.loginPreference('subject') or 'Confirm user',
                                    async_=False,html=True,scheduler=False)
        self.db.commit()
        return 'ok'
        
    @public_method
    def login_confirmNewPassword(self, email=None,username=None, **kwargs):
        usertbl = self.db.table('adm.user')
        if username:
            users = usertbl.query(columns='$id', where='$username = :u', u=username).fetch()
        else:
            users = usertbl.query(columns='$id', where='$email = :e', e=email).fetch()
        if not users:
            return 'err'
        mailservice = self.getService('mail')
        tpl_new_password_id = self.loginPreference('tpl_new_password_id')
        for u in users:
            userid = u['id']
            recordBag = usertbl.record(userid).output('bag')
            if recordBag['status']!='conf':
                return 'err'
            recordBag['link'] = self.externalUrlToken(self.site.homepage, userid=recordBag['id'],max_usages=1)
            recordBag['greetings'] = recordBag['firstname'] or recordBag['lastname']
            body = self.loginPreference('confirm_password_tpl') or 'Dear $greetings set your password $link'
            if tpl_new_password_id:
                mailservice.sendUserTemplateMail(record_id=recordBag,template_id=tpl_new_password_id,
                                                 async_=False,html=True,scheduler=False)
            else:
                mailservice.sendmail_template(recordBag,to_address=email,
                                        body=body, subject=self.loginPreference('confirm_password_subject') or 'Password recovery',
                                        async_=False,html=True,scheduler=False)
            self.db.commit()

        return 'ok'
            #self.sendMailTemplate('confirm_new_pwd.xml', recordBag['email'], recordBag)

    @public_method
    def login_changePassword(self,password=None,gnrtoken=None,current_password=None,newusername=None,**kwargs):
        if gnrtoken:
            method,args,kwargs,user_id = self.db.table('sys.external_token').use_token(gnrtoken)
            if not kwargs:
                return
            userid = kwargs.get('userid')
        else:
            if self.avatar and self.login_checkPwd(self.avatar.user,password=current_password):
                userid = self.avatar.user_id
            else:
                return 'Wrong password'
        if userid:
            updater = dict(status='conf',md5pwd=password)
            if newusername:
                updater['username'] = newusername
            self.db.table('adm.user').batchUpdate(updater,_pkeys=userid)
            self.db.commit()


    @struct_method
    def login_screenLockDialog(self,pane):
        dlg = pane.dialog(_class='lightboxDialog loginDialog',subscribe_screenlock="this.widget.show();this.setRelativeData('.password',null);",datapath='_screenlock')
        box = dlg.div(**self.loginboxPars())
        box.div(text_align='center').cover_logo(height='40px')

        wtitle = '!!Screenlock'
        box.div(wtitle,_class='index_logintitle')  
        box.div('!!Insert password',text_align='center',font_size='.9em',font_style='italic')
        fb = box.div(margin='10px',_class='login_form_container').formbuilder(cols=1, border_spacing='4px',onEnter='FIRE .checkPwd;',
                                width='100%',
                                fld_width='100%',row_height='3ex')
        fb.passwordTextBox(value='^.password',lbl='!!Password',row_hidden=False)
        btn=fb.div(width='100%',position='relative',row_hidden=False).button('!!Enter',action='FIRE .checkPwd;this.widget.setAttribute("disabled",true);',position='absolute',right='-5px',top='8px')
        box.div().slotBar('*,messageBox,*',messageBox_subscribeTo='failed_screenout',height='18px',width='100%',tdl_width='6em')
        fb.dataRpc('.result',self.login_checkPwd,password='=.password',user='=gnr.avatar.user',_fired='^.checkPwd')
        fb.dataController("""if(!authResult){
                                genro.publish('failed_screenout',{'message':error_msg});
                            }else{
                                dlg.hide();
                            }
                            btn.setAttribute('disabled',false);
                            
                            """,authResult='^.result',btn=btn,dlg=dlg.js_widget,error_msg='!!Wrong password')

    @public_method  
    def login_checkPwd(self,user=None,password=None):
        validpwd = self.application.getAvatar(user, password=password,authenticate=True)
        if not validpwd:
            return False
        return True

