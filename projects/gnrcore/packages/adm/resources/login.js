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
    },

    confirmAvatar:(sourceNode,rpcmethod,closable_login,dlg,doLogin,error_msg)=>{
        var avatar = sourceNode.getRelativeData('gnr.avatar');
        var rootenv = sourceNode.getRelativeData('gnr.rootenv');
        var rootpage = rootenv.getItem('rootpage');
        var login = sourceNode.getRelativeData('_login');
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
        genro.serverCall(rpcmethod,{'rootenv':rootenv,login:login},function(result){
            genro.lockScreen(false,'login');
            if (!result || result.error){
                dlg.show();
                genro.publish('failed_login_msg',{'message':result?result.error:error_msg});
            }else{
                genro.setData('gnr.avatar',new gnr.GnrBag(result))
                var user_dbstore = genro.getData('gnr.avatar.user_record.dbstore')
                rootpage = rootpage || result['rootpage'];
                if(user_dbstore){
                    if(!window.location.pathname.slice(1).startsWith(user_dbstore)){
                        var redirect_url = window.location.protocol+'//'+window.location.host+'/'+user_dbstore;
                        if(rootpage){
                            redirect_url+=rootpage;
                        }
                        window.location.assign(redirect_url);
                        return;
                    }
                }
                if(rootpage){
                    genro.gotoURL(rootpage);
                }
                if(doLogin){
                    if(!closable_login){
                        var rootpage = avatar.getItem('avatar_rootpage') || avatar.get('singlepage');
                        if(rootpage){
                            genro.gotoURL(rootpage);
                        }else{
                            genro.pageReload();
                        }
                    }
                }
            }
        },null,'POST');
    }
};
