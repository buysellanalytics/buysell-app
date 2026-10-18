// Buy&Sell: служба для системных уведомлений (docs/23). Ничего не кэширует и не перехватывает запросы —
// только показывает уведомления и по нажатию открывает программу (Android и iPhone «на экране Домой» умеют уведомления только через неё).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const go = (e.notification.data && e.notification.data.go) || '';
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    const w = list.find(c => c.url.startsWith(self.registration.scope));
    if (w) { w.postMessage({ bsNotif: go }); return w.focus(); }
    return self.clients.openWindow(self.registration.scope + (go ? '#' + go : ''));
  }));
});
