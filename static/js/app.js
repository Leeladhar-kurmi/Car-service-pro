document.addEventListener('DOMContentLoaded', () => {
    initMileageInputs();
    initCostFields();
    initPWAInstallPrompt();
});

function initPWAInstallPrompt() {
    let deferredPrompt = null;
    const installPromptEl = document.querySelector('.install-prompt');
    const installBtn = document.getElementById('install-btn');
    const installCloseBtn = document.getElementById('install-close-btn');

    function isInstalledOnDevice() {
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true ||  // iOS Safari
               document.referrer.startsWith('android-app://');
    }

    function showInstallPrompt() {
        if (!isInstalledOnDevice()) {
            installPromptEl?.classList.add('show');
            installPromptEl.style.display = 'block';
        }
    }

    function hideInstallPrompt() {
        installPromptEl?.classList.remove('show');
        installPromptEl.style.display = 'none';
    }

    // Check on load
    if (isInstalledOnDevice()) {
        hideInstallPrompt();
        localStorage.setItem('appInstalled', 'true');
    } else {
        localStorage.removeItem('appInstalled');
    }

    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
        if (isInstalledOnDevice()) return;

        e.preventDefault(); // Stop default banner
        deferredPrompt = e;
        showInstallPrompt();
    });

    // When installed
    window.addEventListener('appinstalled', () => {
        hideInstallPrompt();
        localStorage.setItem('appInstalled', 'true');
        deferredPrompt = null;
    });

    // Install button click
    installBtn?.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            if (result.outcome === 'accepted') {
                hideInstallPrompt();
                localStorage.setItem('appInstalled', 'true');
            }
            deferredPrompt = null;
        } else {
            hideInstallPrompt();
        }
    });

    // Close button
    installCloseBtn?.addEventListener('click', () => {
        hideInstallPrompt();
    });
}


// ===== MILEAGE FORMATTER =====
function initMileageInputs() {
    const mileageInputs = document.querySelectorAll('.mileage-input');
    const MAX_MILEAGE = 999999;

    mileageInputs.forEach(input => {
        if (input.value) {
            input.value = formatMileageNumber(input.value);
        }

        input.addEventListener('keypress', function (e) {
            if (!/\d/.test(e.key) &&
                !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                e.preventDefault();
            }

            const currentValue = this.value.replace(/,/g, '');
            const newValue = currentValue + e.key;
            if (parseInt(newValue) > MAX_MILEAGE) {
                e.preventDefault();
                this.setCustomValidity(`Max mileage is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
        });

        input.addEventListener('paste', function (e) {
            const pasted = (e.clipboardData || window.clipboardData).getData('text');
            if (!/^\d+$/.test(pasted) || parseInt(pasted) > MAX_MILEAGE) {
                e.preventDefault();
                this.setCustomValidity(`Max mileage is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
        });

        input.addEventListener('input', function () {
            let value = this.value.replace(/\D/g, '');
            if (parseInt(value) > MAX_MILEAGE) value = MAX_MILEAGE.toString();
            this.value = formatMileageNumber(value);
            this.setCustomValidity('');
        });

        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function (e) {
                const raw = input.value.replace(/,/g, '');
                if (raw === '' || isNaN(raw) || parseInt(raw) > MAX_MILEAGE) {
                    input.setCustomValidity('Enter valid mileage');
                    input.reportValidity();
                    e.preventDefault();
                    return;
                }
                input.value = raw;
            });
        }
    });
}

function formatMileageNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ===== DYNAMIC COST FIELDS =====
function initCostFields() {
    const select = document.getElementById("service_type_ids");
    const container = document.getElementById("dynamic-cost-fields");
    const totalInput = document.getElementById("total_cost");

    if (!select || !container || !totalInput) return;

    function updateCostFields() {
        container.innerHTML = '';
        [...select.selectedOptions].forEach(option => {
            const id = option.value;
            const label = option.text;
            const div = document.createElement('div');
            div.className = 'mb-2';
            div.innerHTML = `
                <label>Cost for ${label}</label>
                <input type="number" name="cost_${id}" class="form-control cost-field" min="0" step="0.01" value="0">
            `;
            container.appendChild(div);
        });
        attachCostListeners();
    }

    function attachCostListeners() {
        const costFields = container.querySelectorAll('.cost-field');
        const updateTotal = () => {
            let total = 0;
            costFields.forEach(f => total += parseFloat(f.value || 0));
            totalInput.value = total.toFixed(2);
        };
        costFields.forEach(f => f.addEventListener('input', updateTotal));
        updateTotal();
    }

    select.addEventListener('change', updateCostFields);
    updateCostFields();
}
