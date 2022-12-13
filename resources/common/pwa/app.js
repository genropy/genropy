if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register("/_pwa_worker.js")
    .then((reg)=>console.log('registered service worker',reg))
    .catch((error)=>console.error('Not registered service'));
}