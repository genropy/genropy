/*
 * module genro_genroapp : what a page asks GenroApp, the desktop app that opens the site
 *
 * API:
 *   genro.genroapp.tauri()        the bridge of GenroApp, null in a browser
 *   genro.genroapp.confirm(text)  Promise of true when the logged user confirmed text with the
 *                                 identity check of the computer and the site verified it
 *
 * The server method that acts on text calls adm.user_device.popConfirmed(text) before acting:
 * the true of the page alone proves nothing.
 */
dojo.declare("gnr.GnrGenroAppHandler", null, {
    constructor: function(application) {
        this.application = application;
    },

    // GenroApp gives window.__TAURI__ to the page, or to its top window
    tauri:function(){
        if(window.__TAURI__){
            return window.__TAURI__;
        }
        try{
            return window.top.__TAURI__ || null;
        }catch(e){
            return null;
        }
    },

    serverCall:function(method,kwargs){
        return new Promise(function(resolve){
            genro.serverCall(method,kwargs || {},resolve,null,'POST');
        });
    },

    // text: one line of at most 120 characters, without spaces at its ends ("Approve payment 1234").
    // false in a browser, on a computer that is not registered for the user, when the user
    // cancels the identity check and when the site refuses the signature.
    confirm:async function(text){
        var tauri = this.tauri();
        if(!tauri){
            return false;
        }
        var challenge = await this.serverCall('_table.adm.user_device.confirmChallenge',{text:text});
        if(!challenge){
            return false;
        }
        var signed;
        try{
            signed = await tauri.core.invoke('device_confirm',{origin:window.location.origin,
                                                               challenge:challenge,text:text});
        }catch(e){
            return false;
        }
        var confirmed = await this.serverCall('_table.adm.user_device.confirmSigned',
                                              {key_id:signed.key_id,signature:signed.signature,
                                               connector_id:signed.connector_id});
        return confirmed===true;
    }
});
