// Service Worker for PWA functionality
const CACHE_NAME = 'car-service-reminder-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/push-notifications.js',
    '/static/icons/icon-192.svg',
    '/static/icons/icon-512.svg',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/feather-icons@4.28.0/dist/feather.min.js'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Return cached version or fetch from network
                if (response) {
                    return response;
                }
                return fetch(event.request);
            }
        )
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Push event - handle push notifications
self.addEventListener('push', function(event) {
    if (event.data) {
        const notificationData = event.data.json();
        
        const options = {
            body: notificationData.body,
            icon: notificationData.icon || '/static/icons/icon-192.svg',
            badge: notificationData.badge || '/static/icons/icon-192.svg',
            tag: notificationData.tag || 'service-reminder',
            requireInteraction: notificationData.requireInteraction || false,
            actions: notificationData.actions || [],
            data: {
                url: notificationData.url || '/'
            }
        };

        event.waitUntil(
            self.registration.showNotification(notificationData.title, options)
        );
    }
});

// Notification click event
self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    if (event.action === 'view') {
        // Open the app
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    } else if (event.action === 'dismiss') {
        // Just close the notification
        return;
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});

// Background sync for offline actions
self.addEventListener('sync', function(event) {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

function doBackgroundSync() {
    // Handle any offline actions when back online
    console.log('Background sync triggered');
}
