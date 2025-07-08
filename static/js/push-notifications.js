class PushNotificationManager {
  constructor() {
    this.publicVapidKey = null;
    this.isSubscribed = false;
    this.swRegistration = null;
    
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      this.init();
    } else {
      console.warn('Push notifications are not supported in this browser');
    }
  }

  async init() {
    try {
      // 1. Get VAPID public key
      const response = await fetch('/vapid-public-key');
      // console.log("data"+response)
      const data = await response.json();
      // console.log("data"+data)
      this.publicVapidKey = data.key;

      // 2. Register Service Worker
      this.swRegistration = await navigator.serviceWorker.register('/static/js/service-worker.js');
      // console.log('Service Worker registered');

      // 3. Check current subscription status
      await this.updateSubscriptionStatus();

      // 4. Show prompt if permissions not set
      if (Notification.permission === 'default') {
        this.showNotificationPrompt();
      }
    } catch (error) {
      console.error('Push initialization failed:', error);
      this.showStatusMessage('Failed to initialize notifications', 'danger');
    }
  }

  async updateSubscriptionStatus() {
    const subscription = await this.swRegistration.pushManager.getSubscription();
    this.isSubscribed = subscription !== null;
    this.updateUI();
    
    if (this.isSubscribed) {
      console.log('User is subscribed:', subscription);
    }
  }

  async subscribeUser() {
    if (!this.publicVapidKey) {
      throw new Error('VAPID public key not loaded');
    }

    try {
      // 1. Request notification permission
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        throw new Error('Permission not granted');
      }

      // 2. Subscribe to push service
      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.publicVapidKey)
      });

      // 3. Send subscription to server
      await this.sendSubscriptionToServer(subscription);
      
      this.isSubscribed = true;
      this.updateUI();
      // this.showStatusMessage('Notifications enabled!', 'success');
      
      return subscription;
    } catch (error) {
      console.error('Subscription failed:', error);
      // this.showStatusMessage('Failed to enable notifications', 'danger');
      throw error;
    }
  }

  async unsubscribeUser() {
    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
        await this.removeSubscriptionFromServer(subscription);
        this.isSubscribed = false;
        this.updateUI();
        // this.showStatusMessage('Notifications disabled', 'info');
      }
    } catch (error) {
      console.error('Unsubscription failed:', error);
      // this.showStatusMessage('Failed to disable notifications', 'danger');
      throw error;
    }
  }

  async toggleSubscription() {
    if (this.isSubscribed) {
      await this.unsubscribeUser();
    } else {
      await this.subscribeUser();
    }
  }

  async sendTestNotification() {
    if (!this.isSubscribed) {
      // this.showStatusMessage('Please enable notifications first', 'warning');
      return;
    }

    try {
      const response = await fetch('/api/test-notification', { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        // this.showStatusMessage('Test notification sent!', 'success');
      } else {
        throw new Error(await response.text());
      }
    } catch (error) {
      console.error('Test notification failed:', error);
      // this.showStatusMessage('Failed to send test notification', 'danger');
    }
  }

  // Helper methods
  async sendSubscriptionToServer(subscription) {
    await fetch('/api/push-subscription', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription)
    });
  }

  async removeSubscriptionFromServer(subscription) {
    await fetch('/api/push-subscription', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint: subscription.endpoint })
    });
  }

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  updateUI() {
    const toggleBtn = document.getElementById('notification-toggle');
    const statusBadge = document.getElementById('notification-status');
    const permissionBadge = document.getElementById('notification-permission');
    
    if (toggleBtn) {
      toggleBtn.textContent = this.isSubscribed ? 'Disable Notifications' : 'Enable Notifications';
      toggleBtn.className = this.isSubscribed ? 'btn btn-outline-danger' : 'btn btn-primary';
    }
    
    if (statusBadge) {
      statusBadge.textContent = this.isSubscribed ? 'Enabled' : 'Disabled';
      statusBadge.className = this.isSubscribed ? 'badge bg-success' : 'badge bg-secondary';
    }

    if (permissionBadge) {
      permissionBadge.textContent = Notification.permission;
      permissionBadge.className =
        Notification.permission === 'granted' ? 'badge bg-success' :
        Notification.permission === 'denied' ? 'badge bg-danger' :
        'badge bg-warning';
    }
  }

  // showStatusMessage(message, type) {
  //   const alert = document.createElement('div');
  //   alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  //   alert.style.cssText = 'top: 70px; right: 20px; z-index: 9999; min-width: 250px;';
  //   alert.innerHTML = `
  //     ${message}
  //     <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  //   `;
  //   document.body.appendChild(alert);
  //   setTimeout(() => alert.remove(), 3000);
  // }

  showNotificationPrompt() {
    const lastPrompt = localStorage.getItem('lastNotificationPrompt') || 0;
    const now = Date.now();
    
    if (now - lastPrompt > 24 * 60 * 60 * 1000) { // 24 hours cooldown
      const prompt = document.createElement('div');
      prompt.className = 'alert alert-info alert-dismissible fade show position-fixed';
      prompt.style.cssText = 'top: 70px; right: 20px; z-index: 9999; max-width: 350px;';
      prompt.innerHTML = `
        <h6><i class="bi bi-bell"></i> Stay Updated</h6>
        <p class="mb-2 small">Get notified about your car services</p>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-primary" id="enable-notifications-now">Enable</button>
          <button class="btn btn-sm btn-outline-secondary" data-bs-dismiss="alert">Later</button>
        </div>
      `;
      
      document.body.appendChild(prompt);
      localStorage.setItem('lastNotificationPrompt', now.toString());
      
      prompt.querySelector('#enable-notifications-now').addEventListener('click', () => {
        this.subscribeUser();
        prompt.remove();
      });
      
      setTimeout(() => prompt.remove(), 10000);
    }
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const pushManager = new PushNotificationManager();
  
  document.getElementById('notification-toggle')?.addEventListener('click', () => {
    pushManager.toggleSubscription();
  });
  
  document.getElementById('test-notification')?.addEventListener('click', () => {
    pushManager.sendTestNotification();
  });
});