//console.log('inside service worker');
self.addEventListener("install", event => {
  //console.log("Service worker installed");
});
self.addEventListener("activate", event => {
  //console.log("Service worker activated");
});

self.addEventListener("fetch", event => {
  //console.log("Service worker fetch");
});
'use strict';


self.addEventListener('push', event=> {
    console.log('[Service Worker] Push Received.');
    let json =  event.data.json();
    console.log(`[Service Worker] Push had this data: "${json.title}"`);

    const title = json.title;
    const options = {body: json.text,data:json};

event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');
    this.clients.matchAll().then(m=>{console.log('match al result',m)});
    let json = event.notification.data;
    let body =  new URLSearchParams(json);
    fetch(json.confirm_url, {
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
        console.log('notifica accettata')
    });
    event.notification.close();
        //notify to the server the notification has been clicked
    if(json.url){
        event.waitUntil(clients.openWindow(json.url));
    }
    


    
});

self.addEventListener('pushsubscriptionchange', function(event) {
    console.log('[Service Worker]: \'pushsubscriptionchange\' event fired.');
    const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
    const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
    event.waitUntil(
      self.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey
      })
      .then(function(newSubscription) {
        // TODO: Send to application server
        console.log('[Service Worker] New subscription: ', newSubscription);
      })
    );
});