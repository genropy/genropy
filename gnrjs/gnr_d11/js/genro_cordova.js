dojo.declare("gnr.GnrCordovaHandler", null, {
    constructor: function(application) {
        this.application = application;
        for(var k in this){
            if(stringStartsWith(k,'patch_')){
                this[k]();
            }
        }
        this.initialize();
    },

    initialize:function() {
        if(!this.application.getParentGenro()) {
            
            document.addEventListener('deviceready', function() {
                genro.cordova.onDeviceReady();
            }, false);

            var CORDOVA_JS_URL = "https://localhost/cordova.js";
            
            // iOS wants a different scheme for local payloads.
            if(navigator.userAgent.includes("GnriOS")) {
                CORDOVA_JS_URL = "/_cordova_asset/ios/cordova.js";
            }
            genro.dom.loadJs(CORDOVA_JS_URL, () => {
                        console.log("CORDOVA JS LOADED");
            });
        }
    },

    onDeviceReady:function(){
        console.log("CORDOVA JS LOAD COMPLETED");
        console.log('Running cordova-' + cordova.platformId + '@' + cordova.version);
        genro.cordova_ready = true;
        genro.setData("gnr.cordova.platform", cordova.platformId)
        genro.setData("gnr.cordova.version", cordova.version)
        genro.setData("gnr.cordova.ready", true);
        
        if(device) {
            genro.setData("gnr.cordova.device.uuid", device.uuid);
            genro.setData("gnr.cordova.device.model", device.model);
            genro.setData("gnr.cordova.device.manufacturer", device.manufacturer);
        }
        if(universalLinks) {
            universalLinks.subscribe(null, function(eventData) {
                if(genro.framedIndexManager && eventData.params.menucode){
                    let kw = {...eventData.params};
                    genro.framedIndexManager.handleExternalMenuCode(objectPop(kw,'menucode'),kw);
                }else{
                    window.open(eventData.url);
                }
            });
        }
        if(PushNotification) {
            console.log("We have PushNotification");
            genro.notification_obj = PushNotification.init({android: {},
                                    ios: {
                                        alert: 'true',
                                        badge: true,
                                        sound: 'false'
                                    },
                                    });
            PushNotification.hasPermission(function(status) {
                console.log("Push Notification Permission", status)
            });
            genro.notification_obj.on("registration", (data) => {
                console.log("Push Notification registered: ", data);
                genro.setData("gnr.cordova.fcm_push_registration", data);
            });


            genro.notification_obj.on('notification', (data) => {
                let on_click_url = data.additionalData.on_click_url;
                if(on_click_url){
                    fetch(on_click_url, {
                        method: "POST", // *GET, POST, PUT, DELETE, etc.
                        mode: "cors", // no-cors, *cors, same-origin
                        cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
                        credentials: "same-origin", // include, *same-origin, omit
                        headers: {
                          //"Content-Type": "application/json",
                           'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        redirect: "follow", // manual, *follow, error
                        referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
                        body:{message_id:data.additionalData.message_id,page_id:genro.page_id}// body data type must match "Content-Type" header
                    }).then(response=>{
                        console.log('clicked ts set')
                    });
                }
                let url = data.additionalData.url;
                if(url && genro.framedIndexManager){
                    let parsedUrl = parseURL(url);
                    let kw = {...parsedUrl.params};
                    if(kw.menucode){
                        genro.framedIndexManager.handleExternalMenuCode(objectPop(kw,'menucode'),kw);
                        return;
                    }
                }
                if(url){
                    window.open(url);
                }
            });
        }
    }

});
