// Car Service Reminder PWA JavaScript

// PWA Installation
let deferredPrompt;
let installPromptElement;

// Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// PWA Install Prompt
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallPrompt();
});

function showInstallPrompt() {
    // Create install prompt if it doesn't exist
    if (!installPromptElement) {
        installPromptElement = document.createElement('div');
        installPromptElement.className = 'install-prompt';
        installPromptElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>Install Car Service Reminder</strong>
                    <div class="small">Get quick access and offline functionality</div>
                </div>
                <div>
                    <button class="btn btn-sm btn-light me-2" onclick="installApp()">Install</button>
                    <button class="btn btn-sm btn-outline-light" onclick="dismissInstallPrompt()">×</button>
                </div>
            </div>
        `;
        document.body.appendChild(installPromptElement);
    }
    
    // Show the prompt with animation
    setTimeout(() => {
        installPromptElement.classList.add('show');
    }, 2000); // Show after 2 seconds
}

function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted the install prompt');
            } else {
                console.log('User dismissed the install prompt');
            }
            deferredPrompt = null;
            dismissInstallPrompt();
        });
    }
}

function dismissInstallPrompt() {
    if (installPromptElement) {
        installPromptElement.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(installPromptElement);
            installPromptElement = null;
        }, 300);
    }
}

// Handle PWA install event
window.addEventListener('appinstalled', (evt) => {
    console.log('PWA was installed');
    dismissInstallPrompt();
});

// Form Enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Auto-populate service intervals when service type changes
    const serviceTypeSelect = document.getElementById('service_type_id');
    if (serviceTypeSelect) {
        serviceTypeSelect.addEventListener('change', function() {
            populateServiceDefaults(this.value);
        });
    }
    
    // Form validation enhancements
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Auto-save form data to localStorage
    const autoSaveForms = document.querySelectorAll('form[data-autosave]');
    autoSaveForms.forEach(form => {
        const formId = form.getAttribute('data-autosave');
        
        // Load saved data
        loadFormData(form, formId);
        
        // Save on input
        form.addEventListener('input', () => {
            saveFormData(form, formId);
        });
        
        // Clear on submit
        form.addEventListener('submit', () => {
            clearFormData(formId);
        });
    });
    
    // Initialize tooltips and popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-delete') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});

// Service type defaults (this would typically come from the server)
const serviceDefaults = {
    1: { months: 6, mileage: 5000 }, // Oil Change
    2: { months: 6, mileage: 7500 }, // Tire Rotation
    3: { months: 12, mileage: 12000 }, // Brake Inspection
    4: { months: 12, mileage: 12000 }, // Air Filter
    5: { months: 24, mileage: 30000 }, // Transmission Service
    6: { months: 24, mileage: 30000 }, // Coolant Service
    7: { months: 24, mileage: 30000 }, // Spark Plugs
    8: { months: 60, mileage: 60000 }  // Timing Belt
};

function populateServiceDefaults(serviceTypeId) {
    const defaults = serviceDefaults[serviceTypeId];
    if (defaults) {
        const monthsInput = document.getElementById('interval_months');
        const mileageInput = document.getElementById('interval_mileage');
        
        if (monthsInput && !monthsInput.value) {
            monthsInput.value = defaults.months;
        }
        if (mileageInput && !mileageInput.value) {
            mileageInput.value = defaults.mileage;
        }
    }
}

// Form data persistence
function saveFormData(form, formId) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    localStorage.setItem(`form_${formId}`, JSON.stringify(data));
}

function loadFormData(form, formId) {
    const savedData = localStorage.getItem(`form_${formId}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        
        for (let [key, value] of Object.entries(data)) {
            const input = form.querySelector(`[name="${key}"]`);
            if (input && !input.value) {
                input.value = value;
            }
        }
    }
}

function clearFormData(formId) {
    localStorage.removeItem(`form_${formId}`);
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatMileage(mileage) {
    return new Intl.NumberFormat('en-US').format(mileage);
}

// Dashboard updates
function updateDashboard() {
    // This function could be used to periodically update dashboard data
    // For now, we'll just refresh the page
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        // Only auto-refresh on dashboard
        setTimeout(() => {
            window.location.reload();
        }, 300000); // Refresh every 5 minutes
    }
}

// Online/Offline status
window.addEventListener('online', function() {
    console.log('App is online');
    showStatusMessage('Connected', 'success');
});

window.addEventListener('offline', function() {
    console.log('App is offline');
    showStatusMessage('Offline - some features may be unavailable', 'warning');
});

function showStatusMessage(message, type) {
    // Create and show a temporary status message
    const statusEl = document.createElement('div');
    statusEl.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    statusEl.style.cssText = 'top: 70px; right: 20px; z-index: 9999; min-width: 250px;';
    statusEl.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(statusEl);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (statusEl.parentNode) {
            statusEl.remove();
        }
    }, 3000);
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('Car Service Reminder PWA loaded');
    
    // Check if running as PWA
    if (window.matchMedia('(display-mode: standalone)').matches) {
        console.log('Running as PWA');
        document.body.classList.add('pwa-mode');
    }
});
