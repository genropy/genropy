const LoginComponent = {
    onCheckAvatar:(sourceNode,result)=>{
        let avatar = result.getItem('avatar');
        let error_message = result.getItem('login_error_msg');
        if(error_message){
            genro.publish('failed_login_msg',{'message':error_message});
            sourceNode.setRelativeData('gnr.avatar.error' ,error_message);
            return;
        }
        if (!avatar){
            sourceNode.setRelativeData('gnr.avatar', null);
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
        var newenv = result.getItem('rootenv');
        var rootenv = sourceNode.getRelativeData('gnr.rootenv');
        currenv = rootenv.deepCopy();
        currenv.update(newenv);
        sourceNode.setRelativeData('gnr.rootenv', currenv);
        sourceNode.setRelativeData('gnr.avatar',avatar);
        if(avatar.getItem('group_code')){
            sourceNode.setRelativeData('_login.group_code',avatar.getItem('group_code'))
        }
        sourceNode.getValue().walk(n=>{    
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
        }
    },

    confirmAvatar:(sourceNode,rpcmethod,dlg,doLogin,error_msg,standAlonePage)=>{
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
        dlg.hide();
        genro.lockScreen(true,'login');
        let rpckw = {'rootenv':rootenv,login:login};
        genro.serverCall(rpcmethod,rpckw,function(result){
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
                if(doLogin){
                    let avatar_rootpage = avatar.getItem('avatar_rootpage') || avatar.get('singlepage');
                    if(avatar_rootpage && !standAlonePage){
                        genro.gotoURL(avatar_rootpage);
                    }else{
                        genro.pageReload();
                    }
                }else{
                    //different context page
                    genro.pageReload({page_id:genro.page_id});
                }
            }
        },null,'POST');
    }
};
