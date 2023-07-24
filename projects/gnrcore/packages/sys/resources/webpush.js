'use strict';
const WEBPUSH = {};


WEBPUSH.isSubscribed = false;
WEBPUSH.swRegistration = null;

if ('serviceWorker' in navigator && 'PushManager' in window) {
    console.log('Service Worker and Push is supported');
    navigator.serviceWorker.register("/_pwa_worker.js")
        .then(function(swReg) {
            console.log('Service Worker is registered', swReg);
            WEBPUSH.swRegistration = swReg;
        })
        .catch(function(error) {
            console.error('Service Worker Error', error);
        });
} else {
    console.warn('Push meapplicationServerPublicKeyssaging is not supported');
    pushButton.textContent = 'Push Not Supported';
}



WEBPUSH.urlB64ToUint8Array = function(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

WEBPUSH.updateBtn = function {
    if (Notification.permission === 'denied') {
        pushButton.textContent = 'Push Messaging Blocked.';
        pushButton.disabled = true;
        updateSubscriptionOnServer(null);
        return;
    }

    if (WEBPUSH.isSubscribed) {
        pushButton.textContent = 'Disable Push Messaging';
    } else {
        pushButton.textContent = 'Enable Push Messaging';
    }

    pushButton.disabled = false;
}

WEBPUSH.updateSubscriptionOnServer = function(subscription) {
    // TODO: Send subscription to application server

    
    if (subscription) {
        var subscription_token = JSON.stringify(subscription)
        genro.serverCall("_table.sys.push_subscription.store_new_subscription",{subscription_token:subscription_token},
                                                function(result){
                                                    
                                                });
        
    } else {
        genro.serverCall("_table.sys.push_subscription.remove_subscription",{subscription_token:subscription_token},
                                                function(result){
                                                    
                                                });
    }
}

WEBPUSH.notifyAll = function(message_body){
    genro.serverCall("_table.sys.push_subscription.notify_all",{message_body:message_body},
    function(result){
    });
}


WEBPUSH.subscribeUser = function(){
    let vapid_public_key = genro.getData('gnr.vapid_public');
    if (!vapid_public_key){
        genro.serverCall('_table.sys.push_notification.get_vapid_public_key',{},function(vapid_public_key){
            genro.setData('gnr.vapid_public',vapid_public_key);
            WEBPUSH.subscribeUser();
        });
        return
    }
    localStorage.setItem('applicationServerPublicKey',vapid_public_key);
    const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
    const applicationServerKey = WEBPUSH.urlB64ToUint8Array(applicationServerPublicKey);
    WEBPUSH.swRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey
        })
        .then(function(subscription) {
            console.log('User is subscribed.');

            updateSubscriptionOnServer(subscription);
            localStorage.setItem('sub_token',JSON.stringify(subscription));
            WEBPUSH.isSubscribed = true;

            //updateBtn();
        })
        .catch(function(err) {
            console.log('Failed to subscribe the user: ', err);
            //updateBtn();
        });
}

WEBPUSH.unsubscribeUser = function{
    WEBPUSH.swRegistration.pushManager.getSubscription()
        .then(function(subscription) {
            if (subscription) {
                return subscription.unsubscribe();
            }
        })
        .catch(function(error) {
            console.log('Error unsubscribing', error);
        })
        .then(function() {
            updateSubscriptionOnServer(null);

            console.log('User is unsubscribed.');
            WEBPUSH.isSubscribed = false;

            updateBtn();
        });
}

WEBPUSH.initializeUI = function{
    pushButton.addEventListener('click', function() {
        pushButton.disabled = true;
        if (WEBPUSH.isSubscribed) {
            WEBPUSH.unsubscribeUser();
        } else {
            WEBPUSH.subscribeUser();
        }
    });

    // Set the initial subscription value
    WEBPUSH.swRegistration.pushManager.getSubscription()
        .then(function(subscription) {
            WEBPUSH.isSubscribed = !(subscription === null);

            updateSubscriptionOnServer(subscription);

            if (WEBPUSH.isSubscribed) {
                console.log('User IS subscribed.');
            } else {
                console.log('User is NOT subscribed.');
            }

            updateBtn();
        });
}



WEBPUSH.pushMessage = function() {
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
