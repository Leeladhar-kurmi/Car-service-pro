// This is the ONLY service worker file to be used for push notifications.
// Remove or ignore other service worker files (e.g., static/sw.js) to avoid conflicts.

// Service Worker for Vehicle Service Pro

const CACHE_NAME = 'vehicle-service-pro-v1';
// const OFFLINE_URL = '/offline';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/static/css/style.css',
                '/static/js/app.js',
                '/static/icons/icon-192.svg',
                // OFFLINE_URL
            ]);
        })
    );
});

// self.addEventListener('fetch', (event) => {
//     if (event.request.mode === 'navigate') {
//         event.respondWith(
//             fetch(event.request).catch(() => {
//                 return caches.match(OFFLINE_URL);
//             })
//         );
//     } else {
//         event.respondWith(
//             caches.match(event.request).then((response) => {
//                 return response || fetch(event.request);
//             })
//         );
//     }
// });

self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: data.icon || '/static/icons/icon-192.svg',
            badge: '/static/icons/icon-192.svg',
            vibrate: [100, 50, 100],
            data: {
                dateOfArrival: Date.now(),
                primaryKey: 1
            },
            actions: [
                {
                    action: 'explore',
                    title: 'View Details'
                },
                {
                    action: 'close',
                    title: 'Close'
                }
            ]
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/dashboard')
        );
    }
});
