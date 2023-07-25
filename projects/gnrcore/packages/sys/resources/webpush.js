'use strict';
genro.webpush = {};
genro.webpush.swRegistration = null;




genro.webpush.manager = async function(){
    if(genro.webpush.swRegistration){
        return genro.webpush.swRegistration.pushManager;
    }
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        console.log('Service Worker and Push is supported');
        return navigator.serviceWorker.register("/_pwa_worker.js")
            .then(function(swReg) {
                console.log('Service Worker is registered', swReg);
                genro.webpush.swRegistration = swReg;
                return swReg.pushManager;
            })
            .catch(function(error) {
                console.error('Service Worker Error', error);
                return {};
            });
    } else {
        console.warn('Push meapplicationServerPublicKeyssaging is not supported')
        return {};
    }
}


genro.webpush.addSubscriptionOnServer = function(subscription_token) {
    // TODO: Send subscription to application server
    return genro.serverCall("webpushSubscribe",{subscription_token:subscription_token},
                                            function(result){
                                                
                                            });
}


genro.webpush.removeSubscriptionOnServer = function(subscription_token) {
    // TODO: Send subscription to application server
    return genro.serverCall("webpushUnsubscribe",{subscription_token:subscription_token},
                                            function(result){
                                                
                                            });
}

genro.webpush.subscribeUser = function(){
    const vapid_public_key = localStorage.getItem('applicationServerPublicKey');
    if (!vapid_public_key){
        genro.serverCall('webpushGetVapidPublicKey',{},function(vapid_public_key){
            localStorage.setItem('applicationServerPublicKey',vapid_public_key);
            genro.webpush.subscribeUser();
        });
        return
    }
    const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
    const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
    genro.webpush.manager()
        .then(pm=>{
            console.log('pm',pm);
            pm.getSubscription()
                .then(subscription=>{
                    if(!subscription){
                        throw 'no_worker_subscription'
                    }
                    console.log('existing subscription',subscription);
                    genro.webpush.addSubscriptionOnServer(JSON.stringify(subscription))
                })
                .catch(err=>{
                    console.log(err);
                    pm.subscribe({userVisibleOnly: true,applicationServerKey: applicationServerKey})
                           .then(function(subscription) {
                               console.log('User is subscribed.');
                               genro.webpush.addSubscriptionOnServer(JSON.stringify(subscription));
                           })
                           .catch(err=>{
                                console.log("err",err);
                                genro.webpush.unsubscribeUser().then(genro.webpush.subscribeUser);
                           });
                })
        })
}

genro.webpush.unsubscribeUser = function(){
    return genro.webpush.manager().then(pm=>pm.getSubscription()
        .then(function(subscription) {
            if (subscription) {
                subscription.unsubscribe();
                genro.webpush.removeSubscriptionOnServer(JSON.stringify(subscription));
            }
        })
        .catch(function(error) {
            console.log('No push subscription', error);
        }));
}
