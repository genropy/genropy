'use strict';
genro.webpush = {};


genro.webpush.isSubscribed = false;
genro.webpush.swRegistration = null;

if ('serviceWorker' in navigator && 'PushManager' in window) {
    console.log('Service Worker and Push is supported');
    navigator.serviceWorker.register("/_pwa_worker.js")
        .then(function(swReg) {
            console.log('Service Worker is registered', swReg);
            genro.webpush.swRegistration = swReg;
        })
        .catch(function(error) {
            console.error('Service Worker Error', error);
        });
} else {
    console.warn('Push meapplicationServerPublicKeyssaging is not supported');
    pushButton.textContent = 'Push Not Supported';
}


genro.webpush.updateBtn = function() {
    if (Notification.permission === 'denied') {
        pushButton.textContent = 'Push Messaging Blocked.';
        pushButton.disabled = true;
        genro.webpush.updateSubscriptionOnServer(null);
        return;
    }
    if (genro.webpush.isSubscribed) {
        pushButton.textContent = 'Disable Push Messaging';
    } else {
        pushButton.textContent = 'Enable Push Messaging';
    }

    pushButton.disabled = false;
}

genro.webpush.updateSubscriptionOnServer = function(subscription) {
    // TODO: Send subscription to application server
    
    if (subscription) {
        var subscription_token = JSON.stringify(subscription)
        genro.serverCall("webpushSubscribe",{subscription_token:subscription_token},
                                                function(result){
                                                    
                                                });
        
    } else {
        genro.serverCall("webpushUnsubscribe",{subscription_token:subscription_token},
                                                function(result){
                                                    
                                                });
    }
}


genro.webpush.subscribeUser = function(){
    let vapid_public_key = genro.getData('gnr.vapid_public');
    if (!vapid_public_key){
        genro.serverCall('webpushGetVapidPublicKey',{},function(vapid_public_key){
            genro.setData('gnr.vapid_public',vapid_public_key);
            genro.webpush.subscribeUser();
        });
        return
    }
    localStorage.setItem('applicationServerPublicKey',vapid_public_key);
    const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
    const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
    return genro.webpush.swRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey
        })
        .then(function(subscription) {
            console.log('User is subscribed.');

            genro.webpush.updateSubscriptionOnServer(subscription);
            localStorage.setItem('sub_token',JSON.stringify(subscription));
            genro.webpush.isSubscribed = true;

            //updateBtn();
        })
        .catch(function(err) {
            console.log('Failed to subscribe the user: ', err);
            genro.webpush.unsubscribeUser().then(genro.webpush.subscribeUser);
        });
}


genro.webpush.unsubscribeUser = function(){
    return genro.webpush.swRegistration.pushManager.getSubscription()
        .then(function(subscription) {
            if (subscription) {
                return subscription.unsubscribe();
            }
        })
        .catch(function(error) {
            console.log('Error unsubscribing', error);
        })
        .then(function() {
            genro.webpush.updateSubscriptionOnServer(null);
            console.log('User is unsubscribed.');
            genro.webpush.isSubscribed = false;

            updateBtn();
        });
}

genro.webpush.initializeUI = function(){
    pushButton.addEventListener('click', function() {
        pushButton.disabled = true;
        if (genro.webpush.isSubscribed) {
            genro.webpush.unsubscribeUser();
        } else {
            genro.webpush.subscribeUser();
        }
    });

    // Set the initial subscription value
    genro.webpush.swRegistration.pushManager.getSubscription()
        .then(function(subscription) {
            genro.webpush.isSubscribed = !(subscription === null);

            genro.webpush.updateSubscriptionOnServer(subscription);

            if (genro.webpush.isSubscribed) {
                console.log('User IS subscribed.');
            } else {
                console.log('User is NOT subscribed.');
            }

            updateBtn();
        });
}



genro.webpush.pushMessage = function() {
    console.log("sub_token", localStorage.getItem('sub_token'));
    $.ajax({
        type: "POST",
        url: "/push_v1/",
        contentType: 'application/json; charset=utf-8',
        dataType:'json',
        data: JSON.stringify({'sub_token':localStorage.getItem('sub_token')}),
        success: function( data ){
            console.log("success",data);
    },
    error: function( jqXhr, textStatus, errorThrown ){
        console.log("error",errorThrown);
    }
    });
}
//localStorage.setItem('applicationServerPublicKey',genro.getData('gnr.vapid_public'));
