// Car Service Reminder - Core JavaScript
// Uses element detection instead of template blocks

// ===== Global Variables =====
let deferredPrompt = null;
let installPromptElement = null;

// ===== PWA Functionality =====
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => console.log('SW registered:', registration))
            .catch(err => console.log('SW registration failed:', err));
    });
}

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallPrompt();
});

function showInstallPrompt() {
    if (installPromptElement || document.querySelector('.analytics-page')) return;
    
    installPromptElement = document.createElement('div');
    installPromptElement.className = 'install-prompt';
    installPromptElement.innerHTML = `
        <div class="install-prompt-content">
            <button onclick="dismissInstallPrompt()">×</button>
            <p>Install Car Service Pro</p>
            <button onclick="installApp()">Install</button>
        </div>
    `;
    document.body.appendChild(installPromptElement);
}

// ===== Core Initialization =====
document.addEventListener('DOMContentLoaded', function() {
    initCommonComponents();
    
    // Page-specific inits based on element detection
    if (document.getElementById('service_type_ids')) {
        initServiceForm();
    }
    
    if (document.getElementById('costByCarChart')) {
        initAnalyticsCharts();
    }
    
    updateConnectionStatus();
});

// ===== Common Components =====
function initCommonComponents() {
    // Feather Icons
    if (typeof feather !== 'undefined') {
        try {
            feather.replace();
        } catch (e) {
            console.warn('Feather icons error:', e);
        }
    }

    // Tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // Form Validation
    document.querySelectorAll('.needs-validation').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// ===== Service Form =====
function initServiceForm() {
    const serviceTypeSelect = document.getElementById('service_type_ids');
    const costContainer = document.getElementById('dynamic-cost-fields');
    
    if (!serviceTypeSelect || !costContainer) return;

    serviceTypeSelect.addEventListener('change', function() {
        updateCostFields(this);
    });
    
    updateCostFields(serviceTypeSelect);
}

function updateCostFields(selectElement) {
    const costContainer = document.getElementById('dynamic-cost-fields');
    costContainer.innerHTML = '';
    
    Array.from(selectElement.selectedOptions).forEach(option => {
        const field = document.createElement('div');
        field.className = 'mb-3';
        field.innerHTML = `
            <label>${option.text} Cost</label>
            <input type="number" name="cost_${option.value}" 
                   class="form-control cost-field" min="0" step="0.01">
        `;
        costContainer.appendChild(field);
    });
    
    // Add live cost calculation
    document.querySelectorAll('.cost-field').forEach(input => {
        input.addEventListener('input', calculateTotalCost);
    });
}

// ===== Analytics =====
function initAnalyticsCharts() {
    // Chart initialization would go here
    console.log('Initializing analytics charts');
}

// ===== Utility Functions =====
function calculateTotalCost() {
    let total = 0;
    document.querySelectorAll('.cost-field').forEach(input => {
        total += parseFloat(input.value) || 0;
    });
    document.getElementById('total_cost').value = total.toFixed(2);
}

function updateConnectionStatus() {
    const statusEl = document.createElement('div');
    statusEl.className = `connection-status alert alert-${navigator.onLine ? 'success' : 'warning'}`;
    statusEl.textContent = navigator.onLine ? 'Online' : 'Offline';
    document.body.appendChild(statusEl);
}

// ===== Global Methods =====
window.installApp = function() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(choice => {
            if (choice.outcome === 'accepted') {
                console.log('User accepted install');
            }
            deferredPrompt = null;
        });
    }
};

window.dismissInstallPrompt = function() {
    if (installPromptElement) {
        installPromptElement.remove();
        installPromptElement = null;
    }
};