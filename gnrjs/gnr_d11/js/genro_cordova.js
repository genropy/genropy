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
                    if(kw.menucode){
                        let menucode = objectPop(kw,'menucode')
                        genro.framedIndexManager.handleExternalMenuCode(menucode,objectExtract(kw,`${menucode}_*`));
                        return;
                    }
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
                    let bodyData = {message_id: data.additionalData.message_id, page_id: genro.page_id};
                    let formBody = [];
                    for (let property in bodyData) {
                        let encodedKey = encodeURIComponent(property);
                        let encodedValue = encodeURIComponent(bodyData[property]);
                        formBody.push(encodedKey + "=" + encodedValue);
                    }
                    formBody = formBody.join("&");
                    fetch(on_click_url, {
                        method: "POST",
                        mode: "cors",
                        cache: "no-cache",
                        credentials: "same-origin",
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        redirect: "follow",
                        referrerPolicy: "no-referrer",
                        body: formBody
                        }).then(response => {
                            console.log('clicked ts set')
                        });
                }
                let url = data.additionalData.url;
                if(url && genro.framedIndexManager){
                    let parsedUrl = parseURL(url);
                    let kw = {...parsedUrl.params};
                    if(kw.menucode){
                        let menucode = objectPop(kw,'menucode')
                        genro.framedIndexManager.handleExternalMenuCode(menucode,objectExtract(kw,`${menucode}_*`));
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
