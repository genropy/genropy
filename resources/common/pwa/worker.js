'use strict';
//console.log('inside service worker');
self.addEventListener("install", event => {
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

// Some browsers still gate PWA installability on the presence of a fetch listener.
self.addEventListener("fetch", event => {
  //console.log("Service worker fetch");
});

function urlB64ToUint8Array(base64String){
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = self.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

const WPN_DB = 'wpn-config';
const WPN_STORE = 'config';
const WPN_KEY = 'wpn_config';

function wpnDb(){
    return new Promise((resolve, reject)=>{
        const req = indexedDB.open(WPN_DB, 1);
        req.onupgradeneeded = ()=>req.result.createObjectStore(WPN_STORE);
        req.onsuccess = ()=>resolve(req.result);
        req.onerror = ()=>reject(req.error);
    });
}
function wpnConfigPut(cfg){
    return wpnDb().then(db=>new Promise((resolve, reject)=>{
        const tx = db.transaction(WPN_STORE, 'readwrite');
        tx.objectStore(WPN_STORE).put(cfg, WPN_KEY);
        tx.oncomplete = ()=>resolve();
        tx.onerror = ()=>reject(tx.error);
    }));
}
function wpnConfigGet(){
    return wpnDb().then(db=>new Promise((resolve, reject)=>{
        const req = db.transaction(WPN_STORE, 'readonly')
                      .objectStore(WPN_STORE).get(WPN_KEY);
        req.onsuccess = ()=>resolve(req.result || null);
        req.onerror = ()=>reject(req.error);
    }));
}

self.addEventListener('message', event=>{
    const data = event.data || {};
    if(data.type === 'wpn_config'){
        event.waitUntil(wpnConfigPut({
            vapidPublicKey: data.vapidPublicKey || null,
            syncUrl: data.syncUrl || null,
            deviceUuid: data.deviceUuid || null
        }));
    }
});

self.addEventListener('push', event=> {
    console.log('[Service Worker] Push Received.');
    let json =  event.data.json();
    console.log(`[Service Worker] Push had this data: "${json.title}"`);

    const title = json.title;
    const options = {body: json.message || json.text, data:json};
    if(json.icon){options.icon = json.icon;}
    if(json.badge){options.badge = json.badge;}
    if(json.tag){options.tag = json.tag;}
    const on_notified_url = json.on_notified_url;
    const body =  new URLSearchParams(json);
    event.waitUntil(
      
      self.registration.showNotification(title, options).then(
        ()=>{
            if(!on_notified_url){
                return;
            }
            fetch(on_notified_url, {
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
                body:body// body data type must match "Content-Type" header
            }).then(response=>{
                console.log('notified ts set')
            });
            
        }
      )
      
      );
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');
    let json = event.notification.data;
    let body =  new URLSearchParams(json);
    const on_click_url = json.on_click_url;
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
            body:body// body data type must match "Content-Type" header
        }).then(response=>{
            console.log('clicked ts set')
        });
    }
    event.notification.close();
        //notify to the server the notification has been clicked
    if(json.url){
        event.waitUntil(clients.openWindow(json.url));
    }
    


    
});

self.addEventListener('pushsubscriptionchange', event=>{
    event.waitUntil(
        wpnConfigGet().then(cfg=>{
            const oldKey = (event.oldSubscription && event.oldSubscription.options)
                ? event.oldSubscription.options.applicationServerKey : null;
            const appKey = oldKey ||
                ((cfg && cfg.vapidPublicKey) ? urlB64ToUint8Array(cfg.vapidPublicKey) : null);
            if(!appKey){
                return; // no key available: the page-side reconcile will heal
            }
            return self.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: appKey
            }).then(newSubscription=>{
                if(!(cfg && cfg.syncUrl && cfg.deviceUuid)){
                    return; // cannot identify the device: page-side reconcile will heal
                }
                // Best effort: syncUrl embeds the page_id captured at handshake
                // time; if that page has expired the POST fails harmlessly.
                return fetch(cfg.syncUrl, {
                    method: 'POST',
                    credentials: 'same-origin',
                    cache: 'no-cache',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams({
                        device_uuid: cfg.deviceUuid,
                        subscription_token: JSON.stringify(newSubscription),
                        notification_method: 'WPN'
                    })
                });
            });
        }).catch(err=>{
            console.error('[Service Worker] pushsubscriptionchange failed', err);
        })
    );
});