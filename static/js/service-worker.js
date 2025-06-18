// Service Worker for Car Service Pro

const CACHE_NAME = 'car-service-pro-v1';
const OFFLINE_URL = '/offline';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/static/css/style.css',
                '/static/js/app.js',
                '/static/icons/icon-192.svg',
                OFFLINE_URL
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match(OFFLINE_URL);
            })
        );
    } else {
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request);
            })
        );
    }
});

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


document.addEventListener("DOMContentLoaded", function () {
    const serviceTypeSelect = document.getElementById("service_type_ids");
    const costContainer = document.getElementById("dynamic-cost-fields");
    const totalCostInput = document.getElementById("total_cost");

    function updateCostFields() {
        costContainer.innerHTML = "";
        let total = 0;
        [...serviceTypeSelect.selectedOptions].forEach((option, index) => {
            const id = option.value;
            const label = option.text;

            const div = document.createElement("div");
            div.classList.add("mb-2");

            div.innerHTML = `
                <label>Cost for ${label}</label>
                <input type="number" name="cost_${id}" class="form-control cost-field" min="0" step="0.01" value="0">
            `;

            costContainer.appendChild(div);
        });

        attachCostListeners();
    }

    function attachCostListeners() {
        const costFields = document.querySelectorAll(".cost-field");
        costFields.forEach(input => {
            input.addEventListener("input", () => {
                let total = 0;
                costFields.forEach(f => total += parseFloat(f.value || 0));
                totalCostInput.value = total.toFixed(2);
            });
        });
    }

    serviceTypeSelect.addEventListener("change", updateCostFields);
});
