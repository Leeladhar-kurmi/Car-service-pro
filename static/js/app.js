document.addEventListener('DOMContentLoaded', function () {
    initMileageInputs();
    initCostFields();
});

// ===== Mileage Formatting & Validation =====
function initMileageInputs() {
    const mileageInputs = document.querySelectorAll('.mileage-input');
    const MAX_MILEAGE = 999999;

    mileageInputs.forEach(input => {
        if (input.value) {
            input.value = formatMileageNumber(input.value);
        }

        // Restrict invalid keypress
        input.addEventListener('keypress', function (e) {
            if (!/[\d]/.test(e.key) &&
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

        // Prevent non-numeric paste
        input.addEventListener('paste', function (e) {
            const pastedData = (e.clipboardData || window.clipboardData).getData('text');
            if (!/^\d*$/.test(pastedData) || parseInt(pastedData) > MAX_MILEAGE) {
                e.preventDefault();
                this.setCustomValidity(`Max mileage is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
        });

        // Live formatting on input
        input.addEventListener('input', function () {
            let value = this.value.replace(/\D/g, '');
            if (parseInt(value) > MAX_MILEAGE) {
                value = MAX_MILEAGE.toString();
            }
            this.value = formatMileageNumber(value);
            this.setCustomValidity('');
        });

        // On form submit, strip formatting
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function () {
                const rawValue = input.value.replace(/,/g, '');
                if (rawValue === '' || isNaN(rawValue) || parseInt(rawValue) > MAX_MILEAGE) {
                    input.setCustomValidity('Enter valid mileage up to ' + MAX_MILEAGE);
                    input.reportValidity();
                    event.preventDefault();
                    return;
                }
                input.value = rawValue;
            });
        }
    });
}

function formatMileageNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// ===== Cost Field Handling =====
function initCostFields() {
    const serviceTypeSelect = document.getElementById("service_type_ids");
    const costContainer = document.getElementById("dynamic-cost-fields");
    const totalCostInput = document.getElementById("total_cost");

    if (!serviceTypeSelect || !costContainer || !totalCostInput) return;

    function updateCostFields() {
        costContainer.innerHTML = "";
        let total = 0;

        [...serviceTypeSelect.selectedOptions].forEach((option) => {
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

        // Trigger once to calculate total from pre-filled values
        let total = 0;
        costFields.forEach(f => total += parseFloat(f.value || 0));
        totalCostInput.value = total.toFixed(2);
    }

    serviceTypeSelect.addEventListener("change", updateCostFields);

    // Run once on load (for edit page)
    updateCostFields();
}
