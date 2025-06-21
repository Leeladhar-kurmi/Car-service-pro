// Push Notifications for Car Service Reminder PWA

class PushNotificationManager {
    constructor() {
        this.publicVapidKey = null; // Will be set from server
        this.isSubscribed = false;
        this.swRegistration = null;
        
        this.init();
    }
    
    async init() {
        if (!('serviceWorker' in navigator)) {
            // console.log('Service Worker not supported');
            return;
        }
        
        if (!('PushManager' in window)) {
            // console.log('Push messaging not supported');
            return;
        }
        
        try {
            // Wait for service worker to be ready
            this.swRegistration = await navigator.serviceWorker.ready;
            // console.log('Service Worker is ready');
            
            // Check current subscription status
            await this.updateSubscriptionStatus();
            
            // Show notification permission prompt if needed
            this.showNotificationPrompt();
            
        } catch (error) {
            console.error('Error initializing push notifications:', error);
        }
    }
    
    async updateSubscriptionStatus() {
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            this.isSubscribed = !(subscription === null);
            
            // console.log('Subscription status:', this.isSubscribed);
            
            if (this.isSubscribed) {
                // console.log('User is subscribed to push notifications');
            } else {
                // console.log('User is not subscribed to push notifications');
            }
            
            this.updateUI();
        } catch (error) {
            console.error('Error checking subscription status:', error);
        }
    }
    
    async subscribeUser() {
        if (!this.publicVapidKey) {
            console.error('VAPID public key not available');
            return false;
        }
        
        try {
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.publicVapidKey)
            });
            
            // console.log('User subscribed to push notifications');
            
            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
            
            this.isSubscribed = true;
            this.updateUI();
            
            return true;
        } catch (error) {
            console.error('Failed to subscribe user:', error);
            return false;
        }
    }
    
    async unsubscribeUser() {
        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            
            if (subscription) {
                await subscription.unsubscribe();
                // console.log('User unsubscribed from push notifications');
                
                // Remove subscription from server
                await this.removeSubscriptionFromServer();
                
                this.isSubscribed = false;
                this.updateUI();
                
                return true;
            }
        } catch (error) {
            console.error('Error unsubscribing:', error);
            return false;
        }
    }
    
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscription)
            });
            
            if (!response.ok) {
                throw new Error('Failed to send subscription to server');
            }
            
            // console.log('Subscription sent to server successfully');
        } catch (error) {
            console.error('Error sending subscription to server:', error);
            throw error;
        }
    }
    
    async removeSubscriptionFromServer() {
        try {
            const response = await fetch('/api/push-subscription', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to remove subscription from server');
            }
            
            // console.log('Subscription removed from server successfully');
        } catch (error) {
            console.error('Error removing subscription from server:', error);
        }
    }
    
    updateUI() {
        const notificationToggle = document.getElementById('notification-toggle');
        const notificationStatus = document.getElementById('notification-status');
        
        if (notificationToggle) {
            notificationToggle.textContent = this.isSubscribed ? 'Disable Notifications' : 'Enable Notifications';
            notificationToggle.className = this.isSubscribed ? 'btn btn-outline-danger' : 'btn btn-primary';
        }
        
        if (notificationStatus) {
            notificationStatus.textContent = this.isSubscribed ? 'Enabled' : 'Disabled';
            notificationStatus.className = this.isSubscribed ? 'badge bg-success' : 'badge bg-secondary';
        }
    }
    
    showNotificationPrompt() {
        // Show notification permission prompt after user interaction
        if (Notification.permission === 'default') {
            this.createNotificationPrompt();
        }
    }
    
    createNotificationPrompt() {
        // Only show if user is logged in and hasn't been prompted recently
        if (!document.body.classList.contains('user-authenticated')) {
            return;
        }
        
        const lastPrompt = localStorage.getItem('lastNotificationPrompt');
        const now = Date.now();
        const oneDayAgo = now - (24 * 60 * 60 * 1000);
        
        if (lastPrompt && parseInt(lastPrompt) > oneDayAgo) {
            return; // Don't show prompt more than once per day
        }
        
        const promptEl = document.createElement('div');
        promptEl.className = 'alert alert-info alert-dismissible fade show position-fixed';
        promptEl.style.cssText = 'top: 70px; right: 20px; z-index: 9999; max-width: 350px;';
        promptEl.innerHTML = `
            <h6><i data-feather="bell"></i> Stay Updated</h6>
            <p class="mb-2 small">Get notified when your car services are due</p>
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-primary" onclick="pushManager.requestNotificationPermission()">
                    Enable Notifications
                </button>
                <button class="btn btn-sm btn-outline-secondary" data-bs-dismiss="alert">
                    Maybe Later
                </button>
            </div>
        `;
        
        document.body.appendChild(promptEl);
        
        // Update icons if feather is available
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
        
        // Store that we showed the prompt
        localStorage.setItem('lastNotificationPrompt', now.toString());
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (promptEl.parentNode) {
                promptEl.remove();
            }
        }, 10000);
    }
    
    async requestNotificationPermission() {
        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                // console.log('Notification permission granted');
                await this.subscribeUser();
                this.showStatusMessage('Notifications enabled successfully!', 'success');
            } else {
                // console.log('Notification permission denied');
                this.showStatusMessage('Notification permission denied', 'warning');
            }
        } catch (error) {
            console.error('Error requesting notification permission:', error);
        }
    }
    
    async toggleSubscription() {
        if (this.isSubscribed) {
            await this.unsubscribeUser();
        } else {
            if (Notification.permission === 'granted') {
                await this.subscribeUser();
            } else {
                await this.requestNotificationPermission();
            }
        }
    }
    
    // Test notification (for development)
    async sendTestNotification() {
        if (!this.isSubscribed) {
            // console.log('User not subscribed to notifications');
            return;
        }
        
        try {
            const response = await fetch('/api/test-notification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // console.log('Test notification sent');
            } else {
                console.error('Failed to send test notification');
            }
        } catch (error) {
            console.error('Error sending test notification:', error);
        }
    }
    
    showStatusMessage(message, type) {
        const statusEl = document.createElement('div');
        statusEl.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        statusEl.style.cssText = 'top: 70px; right: 20px; z-index: 9999; min-width: 250px;';
        statusEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(statusEl);
        
        setTimeout(() => {
            if (statusEl.parentNode) {
                statusEl.remove();
            }
        }, 3000);
    }
    
    // Utility function to convert VAPID key
    urlBase64ToUint8Array(base64String) {
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
}

// Initialize push notification manager
let pushManager;

document.addEventListener('DOMContentLoaded', function() {
    pushManager = new PushNotificationManager();
    
    // Add event listeners for notification controls
    const notificationToggle = document.getElementById('notification-toggle');
    if (notificationToggle) {
        notificationToggle.addEventListener('click', () => {
            pushManager.toggleSubscription();
        });
    }
    
    // Add test notification button for development
    const testNotificationBtn = document.getElementById('test-notification');
    if (testNotificationBtn) {
        testNotificationBtn.addEventListener('click', () => {
            pushManager.sendTestNotification();
        });
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

