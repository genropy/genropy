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

    deviceLogin:async (sourceNode,challenge_rpc,login_rpc)=>{
        const tauri = LoginComponent.tauri();
        if(!tauri){
            return;
        }
        const origin = window.location.origin;
        const status = await tauri.core.invoke('device_status',{origin});
        if(!status.registered){
            return;
        }
        let signed;
        try{
            const challenge = await LoginComponent.serverCall(challenge_rpc);
            signed = await tauri.core.invoke('device_sign',{origin,challenge});
        }catch{
            // biometric reading cancelled or failed: the normal login stays available
            return;
        }
        const result = await LoginComponent.serverCall(login_rpc,{key_id:signed.key_id,user:signed.user,
                                                                   signature:signed.signature});
        if(!result){
            genro.publish('failed_login_msg',{message:_T('!![en]This computer is not recognized: log in with password')});
            return;
        }
        sourceNode.setRelativeData('_login.device_user',result.getItem('user'));
        sourceNode.setRelativeData('_login.user',result.getItem('user'));
        if(result.getItem('mode')=='signature'){
            genro.fireEvent('do_login_check');
        }
    },

    askDeviceRegistration:()=>{
        return new Promise(resolve=>{
            genro.dlg.ask(_T('!![en]GenroApp'),_T('!![en]Register this computer for the next logins?'),
                          {confirm:_T('!![en]Register'),cancel:_T('!![en]Not now')},
                          {confirm:()=>resolve(true),cancel:()=>resolve(false)});
        });
    },

    // true when the login may go on: the computer is registered, or its registration
    // was only offered
    deviceRegistration:async (registration,user,device_rpc)=>{
        const tauri = LoginComponent.tauri();
        if(!tauri){
            return registration!='required';
        }
        const origin = window.location.origin;
        const status = await tauri.core.invoke('device_status',{origin});
        if(registration=='offer' && (status.registered || !await LoginComponent.askDeviceRegistration())){
            return true;
        }
        let registered;
        try{
            const challenge = await LoginComponent.serverCall(device_rpc.challenge);
            registered = await tauri.core.invoke('device_register',{origin,user,challenge});
        }catch{
            // biometric reading cancelled or failed: only an offered registration lets the login go on
            return registration!='required';
        }
        const ok = await LoginComponent.serverCall(device_rpc.register,{
            key_id:registered.key_id,public_key:registered.public_key,alg:registered.alg,
            device_name:registered.device_name,platform:status.platform,
            verification:registered.verification,signature:registered.signature});
        return !!ok || registration!='required';
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
        if(registration && !await LoginComponent.deviceRegistration(registration,login.getItem('user'),device_rpc)){
            genro.publish('failed_login_msg',{'message':_T('!![en]This user must log in with GenroApp')});
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
