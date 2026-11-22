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

    // a full-window screen with the logo and the title of the login dialog: a title, an
    // optional line, one button and an optional link
    fullScreen:(dlg,{title,line,button,link})=>{
        const make = (tag,cls,text,parent)=>{
            const node = document.createElement(tag);
            node.className = cls;
            if(text){
                node.textContent = text;
            }
            parent.appendChild(node);
            return node;
        };
        const screen = document.createElement('div');
        screen.className = 'genroapp_lockscreen';
        const box = make('div','genroapp_lockscreen_box',null,screen);
        const logo = dlg.domNode.querySelector('.login_logo');
        if(logo){
            const logo_copy = logo.cloneNode(true);
            logo_copy.className = 'genroapp_lockscreen_logo';
            box.appendChild(logo_copy);
        }
        const site_title = dlg.domNode.querySelector('.index_logintitle');
        make('div','genroapp_lockscreen_site',site_title? site_title.textContent : document.title,box);
        make('div','genroapp_lockscreen_title',title,box);
        if(line){
            make('div','genroapp_lockscreen_line',line,box);
        }
        const button_node = make('button','genroapp_lockscreen_unlock',button,box);
        let link_node = null;
        if(link){
            link_node = make('a','genroapp_lockscreen_password',link,box);
            link_node.href = '#';
        }
        document.body.appendChild(screen);
        button_node.focus();
        return {button:button_node,link:link_node,close:()=>screen.remove()};
    },

    // after a logout the biometric reading is not asked at once: the lock screen lets the
    // user choose
    lockScreen:(dlg,platform,onUnlock,onPassword)=>{
        const screen = LoginComponent.fullScreen(dlg,{
            title:_T('!![en]Session closed'),
            button:_T('!![en]Unlock with {biometry}').replace('{biometry}',LoginComponent.biometryName(platform)),
            link:_T('!![en]Log in with password')
        });
        screen.button.onclick = ()=>onUnlock(screen.close);
        screen.link.onclick = (e)=>{
            e.preventDefault();
            screen.close();
            onPassword();
        };
    },

    // asks the biometric reading and logs in with the signature; false when the reading is
    // cancelled or fails, or the device is not recognized
    deviceSign:async (sourceNode,dlg,origin,challenge_rpc,login_rpc)=>{
        const tauri = LoginComponent.tauri();
        let signed;
        try{
            const challenge = await LoginComponent.serverCall(challenge_rpc);
            signed = await tauri.core.invoke('device_sign',{origin,challenge});
        }catch{
            return false;
        }
        const result = await LoginComponent.serverCall(login_rpc,{key_id:signed.key_id,user:signed.user,
                                                                   signature:signed.signature});
        if(!result){
            genro.publish('failed_login_msg',{message:_T('!![en]This device is not recognized: log in with password')});
            return false;
        }
        sourceNode.setRelativeData('_login.device_user',result.getItem('user'));
        sourceNode.setRelativeData('_login.user',result.getItem('user'));
        if(result.getItem('mode')=='signature'){
            // the dialog stays hidden: a failed login shows it again (failed_login_msg)
            genro.fireEvent('do_login_check');
        }else{
            LoginComponent.hideLoginDialog(dlg,false);
        }
        return true;
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
        const sign = ()=>LoginComponent.deviceSign(sourceNode,dlg,origin,challenge_rpc,login_rpc);
        if(after_logout){
            // the lock screen stays until the reading succeeds or the user picks the password
            LoginComponent.lockScreen(dlg,status.platform,
                                      async close=>{
                                          if(await sign()){
                                              close();
                                          }
                                      },
                                      ()=>LoginComponent.hideLoginDialog(dlg,false));
            return;
        }
        if(!await sign()){
            LoginComponent.hideLoginDialog(dlg,false);
        }
    },

    // registers this device: the key is created and its signature sent to the server;
    // true when the server stored the key
    registerDevice:async (origin,user,platform,device_rpc)=>{
        const tauri = LoginComponent.tauri();
        let registered;
        try{
            const challenge = await LoginComponent.serverCall(device_rpc.challenge);
            registered = await tauri.core.invoke('device_register',{origin,user,challenge});
        }catch{
            // biometric reading cancelled or failed
            return false;
        }
        const ok = await LoginComponent.serverCall(device_rpc.register,{
            key_id:registered.key_id,public_key:registered.public_key,alg:registered.alg,
            device_name:registered.device_name,platform:platform,
            verification:registered.verification,signature:registered.signature});
        return !!ok;
    },

    // null when the login may go on, else the message that stops it; inside GenroApp the
    // registration of a device not yet registered is imposed by a full-window screen that
    // stays until the registration succeeds
    deviceRegistration:async (dlg,registration,user,device_rpc)=>{
        const tauri = LoginComponent.tauri();
        if(!tauri){
            return registration=='required'? _T('!![en]This user must log in with GenroApp') : null;
        }
        const origin = window.location.origin;
        const status = await tauri.core.invoke('device_status',{origin});
        if(registration=='offer' && status.registered){
            return null;
        }
        const biometry = LoginComponent.biometryName(status.platform);
        LoginComponent.hideLoginDialog(dlg,true);
        await new Promise(resolve=>{
            const screen = LoginComponent.fullScreen(dlg,{
                title:_T('!![en]Register this device'),
                line:_T('!![en]Next time, unlock with {biometry}.').replace('{biometry}',biometry),
                button:_T('!![en]Register with {biometry}').replace('{biometry}',biometry)
            });
            screen.button.onclick = async ()=>{
                if(await LoginComponent.registerDevice(origin,user,status.platform,device_rpc)){
                    screen.close();
                    resolve();
                }
            };
        });
        LoginComponent.hideLoginDialog(dlg,false);
        return null;
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
                await LoginComponent.deviceRegistration(dlg,registration,login.getItem('user'),device_rpc);
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
