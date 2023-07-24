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
    console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

    const title = 'Notifica Genropy';
    const options = {
      body: `${event.data.text()}`
};

event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');

    event.notification.close();

    event.waitUntil(clients.openWindow('https://developers.google.com/web/'));
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