document.addEventListener('DOMContentLoaded', function () {
    // === Mileage Input Logic ===
    const mileageInputs = document.querySelectorAll('.mileage-input');
    const MAX_MILEAGE = 999999;

    mileageInputs.forEach(input => {
        if (input.value) {
            input.value = formatMileageNumber(input.value);
        }

        input.addEventListener('keypress', function (e) {
            if (!/[\d]/.test(e.key) &&
                !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
                e.preventDefault();
            }

            if (/[\d]/.test(e.key)) {
                const newValue = this.value.replace(/,/g, '') + e.key;
                if (parseInt(newValue) > MAX_MILEAGE) {
                    e.preventDefault();
                    this.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                    this.reportValidity();
                }
            }
        });

        input.addEventListener('paste', function (e) {
            let pasted = (e.clipboardData || window.clipboardData).getData('text');
            if (!/^\d*$/.test(pasted) || parseInt(pasted) > MAX_MILEAGE) {
                e.preventDefault();
                this.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
        });

        input.addEventListener('input', function () {
            let val = this.value.replace(/\D/g, '');
            if (parseInt(val) > MAX_MILEAGE) val = MAX_MILEAGE.toString();
            this.value = formatMileageNumber(val);
            this.setCustomValidity('');
        });

        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function (e) {
                const rawValue = input.value.replace(/,/g, '');
                if (rawValue === '' || isNaN(rawValue) || parseInt(rawValue) > MAX_MILEAGE) {
                    e.preventDefault();
                    input.setCustomValidity(`Please enter a valid mileage up to ${MAX_MILEAGE}`);
                    input.reportValidity();
                } else {
                    input.value = rawValue;
                }
            });
        }
    });

    // === Cost Field Logic ===
    const serviceTypeSelect = document.getElementById("service_type_ids");
    const costContainer = document.getElementById("dynamic-cost-fields");
    const totalCostInput = document.getElementById("total_cost");

    if (serviceTypeSelect && costContainer && totalCostInput) {
        function updateCostFields() {
            costContainer.innerHTML = "";
            [...serviceTypeSelect.selectedOptions].forEach(option => {
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
        updateCostFields();
    }
});

function formatMileageNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
