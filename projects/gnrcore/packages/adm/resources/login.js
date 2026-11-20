const LoginComponent = {
    onCheckAvatar:(sourceNode,result,error_msg,explicitCheck)=>{
        let avatar = result.getItem('avatar');
        let error_message = result.getItem('login_error_msg');
        if(error_message){
            genro.publish('failed_login_msg',{'message':error_message});
            sourceNode.setRelativeData('gnr.avatar.error' ,error_message);
            return;
        }
        if (!avatar){
            sourceNode.setRelativeData('gnr.avatar', null);
            if(explicitCheck){
                genro.publish('failed_login_msg',{'message':error_msg});
            }
            return;
        }
        if(avatar.getItem('status')=='bann'){
            genro.publish('failed_login_msg',{'message':_T('User is banned')});
            sourceNode.setRelativeData('gnr.avatar.error' ,_T('User is banned'));
            return;
        }
        if(avatar.getItem('status')!='conf'){
            sourceNode.setRelativeData('gnr.avatar', avatar);
            genro.publish('confirmUserDialog');
            return;
        }
        if(result.getItem('waiting2fa') && !explicitCheck){
            sourceNode.setRelativeData('gnr.avatar', null);
            return;
        }
        let newenv = result.getItem('rootenv');
        let rootenv = sourceNode.getRelativeData('gnr.rootenv');
        currenv = rootenv.deepCopy();
        currenv.update(newenv);
        sourceNode.setRelativeData('gnr.rootenv', currenv);
        sourceNode.setRelativeData('gnr.avatar',avatar);
        let extraEditableFields = [];

        if(avatar.getItem('group_code')){
            sourceNode.setRelativeData('_login.group_code',avatar.getItem('group_code'))
        }
        sourceNode.getValue().walk(n=>{
            if(genro.dom.isVisible(n) && n.attr.value && n.attr.nodeId!="tb_login_pwd" &&  n.attr.nodeId!="tb_login_user"){
                extraEditableFields.push(n);
            }
            if(!n.hasValidations()){
                return
            }
            let validation = n.validationsOnChange(n,n.getAttributeFromDatasource('value'));;
            if (validation.modified) {
                n.widget.setValue(validation.value);
            }
            n.setValidationError(validation);
            n.updateValidationStatus();

        })
        if(result.getItem('waiting2fa')){
            sourceNode.setRelativeData('waiting2fa',true);
            genro.publish('getOtpDialog');
        }else if(explicitCheck && extraEditableFields.length==0){
            genro.fireEvent('do_login',true);
        }
    },

    hasVisibleFields:(sourceNode)=>{
        let visible = false;
        sourceNode.getValue().walk(n=>{
            if(n.attr.value && !n.getAttributeFromDatasource('hidden')){
                visible = true;
            }
        });
        return visible;
    },

    // GenroApp gives the page window.__TAURI__ (or to its top window): elsewhere none of
    // the device calls below runs
    tauri:()=>{
        if(window.__TAURI__){
            return window.__TAURI__;
        }
        try{
            return window.top.__TAURI__;
        }catch(e){
            return null;
        }
    },

    serverCall:(method,kwargs)=>{
        return new Promise(resolve=>genro.serverCall(method,kwargs || {},resolve,null,'POST'));
    },

    // the name the operating system gives to the biometric reading
    biometryName:(platform)=>{
        return platform=='windows'? 'Windows Hello' : 'Touch ID';
    },

    // the login dialog stays hidden while GenroApp asks the biometric reading
    hideLoginDialog:(dlg,hidden)=>{
        if(hidden){
            genro.dom.addClass(dlg.domNode,'genroapp_signing');
        }else{
            genro.dom.removeClass(dlg.domNode,'genroapp_signing');
        }
    },

    // after a logout the biometric reading is not asked at once: the user chooses
    askAfterLogout:(platform)=>{
        return new Promise(resolve=>{
            genro.dlg.ask(_T('!![en]Session closed'),
                          _T('!![en]You logged out of this application.'),
                          {unlock:_T('!![en]Unlock with {biometry}').replace('{biometry}',
                                                                             LoginComponent.biometryName(platform)),
                           password:_T('!![en]Log in with password')},
                          {unlock:()=>resolve(true),password:()=>resolve(false)},{closable:false});
        });
    },

    deviceLogin:async (sourceNode,dlg,challenge_rpc,login_rpc)=>{
        const tauri = LoginComponent.tauri();
        if(!tauri){
            return;
        }
        const after_logout = genro.loggedOut(true);
        const origin = window.location.origin;
        const status = await tauri.core.invoke('device_status',{origin});
        if(!status.registered){
            return;
        }
        LoginComponent.hideLoginDialog(dlg,true);
        if(after_logout && !await LoginComponent.askAfterLogout(status.platform)){
            LoginComponent.hideLoginDialog(dlg,false);
            return;
        }
        let signed;
        try{
            const challenge = await LoginComponent.serverCall(challenge_rpc);
            signed = await tauri.core.invoke('device_sign',{origin,challenge});
        }catch{
            // biometric reading cancelled or failed: the normal login stays available
            LoginComponent.hideLoginDialog(dlg,false);
            return;
        }
        const result = await LoginComponent.serverCall(login_rpc,{key_id:signed.key_id,user:signed.user,
                                                                   signature:signed.signature});
        if(!result){
            LoginComponent.hideLoginDialog(dlg,false);
            genro.publish('failed_login_msg',{message:_T('!![en]This computer is not recognized: log in with password')});
            return;
        }
        sourceNode.setRelativeData('_login.device_user',result.getItem('user'));
        sourceNode.setRelativeData('_login.user',result.getItem('user'));
        if(result.getItem('mode')=='signature'){
            // the dialog stays hidden: a failed login shows it again (failed_login_msg)
            genro.fireEvent('do_login_check');
        }else{
            LoginComponent.hideLoginDialog(dlg,false);
        }
    },

    imposeDeviceRegistration:(platform)=>{
        const biometry = LoginComponent.biometryName(platform);
        return new Promise(resolve=>{
            const message = [
                _T('!![en]GenroApp keeps a key for this application on this computer.'),
                _T('!![en]Press the button and confirm with {biometry}.'),
                _T('!![en]From the next login {biometry} is enough on this computer: no password.'),
                _T('!![en]On other computers you keep logging in with your password.')
            ].join(' ').replaceAll('{biometry}',biometry);
            genro.dlg.ask(_T('!![en]Register this computer now'),message,
                          {register:_T('!![en]Register this computer now')},
                          {register:()=>resolve()},{closable:false});
        });
    },

    // null when the login may go on, else the message that stops it; inside GenroApp the
    // registration of a computer not yet registered is always imposed
    deviceRegistration:async (registration,user,device_rpc)=>{
        const tauri = LoginComponent.tauri();
        if(!tauri){
            return registration=='required'? _T('!![en]This user must log in with GenroApp') : null;
        }
        const origin = window.location.origin;
        const status = await tauri.core.invoke('device_status',{origin});
        if(registration=='offer' && status.registered){
            return null;
        }
        await LoginComponent.imposeDeviceRegistration(status.platform);
        const failed = _T('!![en]This computer is not registered: the login stops here');
        let registered;
        try{
            const challenge = await LoginComponent.serverCall(device_rpc.challenge);
            registered = await tauri.core.invoke('device_register',{origin,user,challenge});
        }catch{
            // biometric reading cancelled or failed
            return failed;
        }
        const ok = await LoginComponent.serverCall(device_rpc.register,{
            key_id:registered.key_id,public_key:registered.public_key,alg:registered.alg,
            device_name:registered.device_name,platform:status.platform,
            verification:registered.verification,signature:registered.signature});
        return ok? null : failed;
    },

    confirmAvatar:async (sourceNode,rpcmethod,dlg,doLogin,error_msg,standAlonePage,device_rpc)=>{
        var avatar = sourceNode.getRelativeData('gnr.avatar');
        var rootenv = sourceNode.getRelativeData('gnr.rootenv');
        var login = sourceNode.getRelativeData('_login');
        var waiting2fa = genro.getData('waiting2fa')
        if(waiting2fa){
            return;
        }
        if(!avatar || !avatar.getItem('user') || avatar.getItem('error')){
            var error = avatar? (avatar.getItem('error') || error_msg):error_msg
            genro.publish('failed_login_msg',{'message':error});
            return;
        }
        var invalid_fields = [];
        sourceNode.getValue().walk(n=>{
            if(n.hasValidations()){
                let validation = n.validationsOnChange(n,n.getAttributeFromDatasource('value'));
                if(validation.error){
                    invalid_fields.push(n.widget)
                }
            }
        });
        if(invalid_fields.length){
            invalid_fields[0].focus();
            //genro.publish('failed_login_msg',{'message':'Invalid data'});
            return;
        }
        let registration = doLogin && avatar.getItem('device_registration');
        let registration_error = registration &&
                await LoginComponent.deviceRegistration(registration,login.getItem('user'),device_rpc);
        if(registration_error){
            genro.publish('failed_login_msg',{'message':registration_error});
            return;
        }
        dlg.hide();
        genro.lockScreen(true,'login');
        let rpckw = {'rootenv':rootenv,login:login};
        genro.serverCall(rpcmethod,rpckw,function(result){
            let rootenv = sourceNode.getRelativeData('gnr.rootenv');
            genro.lockScreen(false,'login');
            if (!result || result.error){
                dlg.show();
                genro.publish('failed_login_msg',{'message':result?result.error:error_msg});
            }else{
                genro.setData('gnr.avatar',new gnr.GnrBag(result))
                var user_dbstore = genro.getData('gnr.avatar.user_record.dbstore')
                let startPage = result['rootpage'] || sourceNode.getRelativeData('gnr.rootenv.rootpage');
                if(user_dbstore){
                    if(!window.location.pathname.slice(1).startsWith(user_dbstore)){
                        var redirect_url = window.location.protocol+'//'+window.location.host+'/'+user_dbstore;
                        if(rootpage){
                            redirect_url+=startPage;
                        }
                        window.location.assign(redirect_url);
                        return;
                    }
                }
                if(startPage){
                    genro.gotoURL(startPage);
                    return
                }
                let kwreload = Object.fromEntries(new URL(window.location.href).searchParams);
                objectPop(kwreload,'gnrtoken');
                if(doLogin){
                    let singlepage = avatar.getItem('avatar_rootpage') || rootenv.getItem('singlepage');
                    if(singlepage && !standAlonePage){
                        genro.gotoURL(genro.addParamsToUrl(singlepage,kwreload));
                    }else{
                        genro.pageReload();
                    }
                }else{
                    //different context page
                    if(LoginComponent.hasVisibleFields(sourceNode)){
                        kwreload.page_id = genro.page_id;
                    }
                    objectPop(kwreload,'new_window');
                    genro.pageReload(kwreload);
                }
            }
        },null,'POST');
    }
};
