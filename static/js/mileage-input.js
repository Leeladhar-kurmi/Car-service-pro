// Format mileage inputs with commas while keeping the raw number for submission
document.addEventListener('DOMContentLoaded', function() {
    const mileageInputs = document.querySelectorAll('.mileage-input');
    const MAX_MILEAGE = 999999;
    
    mileageInputs.forEach(input => {
        // Format initial value if it exists
        if (input.value) {
            const formatted = formatMileageNumber(input.value);
            input.value = formatted;
        }

        // Prevent non-numeric input
        input.addEventListener('keypress', function(e) {
            // Allow only numbers (0-9) and special keys like backspace, delete, arrows
            if (!/[\d]/.test(e.key) && // If not a number
                e.key !== 'Backspace' && 
                e.key !== 'Delete' && 
                e.key !== 'ArrowLeft' && 
                e.key !== 'ArrowRight' && 
                e.key !== 'Tab') {
                e.preventDefault();
            }

            // Check if adding this digit would exceed the max limit
            if (/[\d]/.test(e.key)) {
                const currentValue = this.value.replace(/,/g, '');
                const newValue = currentValue + e.key;
                if (parseInt(newValue) > MAX_MILEAGE) {
                    e.preventDefault();
                    this.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                    this.reportValidity();
                }
            }
        });

        // Prevent paste of non-numeric values
        input.addEventListener('paste', function(e) {
            // Get pasted data
            let pastedData = (e.clipboardData || window.clipboardData).getData('text');
            if (!/^\d*$/.test(pastedData)) {
                e.preventDefault();
            }
            // Check if pasted value would exceed max limit
            if (parseInt(pastedData) > MAX_MILEAGE) {
                e.preventDefault();
                this.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
        });

        // Handle input changes
        input.addEventListener('input', function(e) {
            // Remove any non-digit characters
            let value = this.value.replace(/\D/g, '');
            
            // Check max limit
            if (parseInt(value) > MAX_MILEAGE) {
                value = MAX_MILEAGE.toString();
                this.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                this.reportValidity();
            }
            
            if (value) {
                // Format the number with commas
                const formatted = formatMileageNumber(value);
                this.value = formatted;
            }
        });

        // Handle form submission
        input.closest('form').addEventListener('submit', function(e) {
            // Get the input value and remove commas
            const rawValue = input.value.replace(/,/g, '');
            
            // Check if the value is a valid number and within limits
            if (rawValue === '' || isNaN(rawValue)) {
                e.preventDefault(); // Prevent form submission
                input.setCustomValidity('Please enter a valid number');
                input.reportValidity();
                return;
            }
            
            const numericValue = parseInt(rawValue);
            if (numericValue > MAX_MILEAGE) {
                e.preventDefault(); // Prevent form submission
                input.setCustomValidity(`Maximum mileage allowed is ${formatMileageNumber(MAX_MILEAGE)}`);
                input.reportValidity();
                return;
            }
            
            // Set the raw numeric value for submission
            input.value = rawValue;
        });

        // Clear validation message when user starts typing
        input.addEventListener('input', function() {
            if (parseInt(this.value.replace(/,/g, '')) <= MAX_MILEAGE) {
                this.setCustomValidity('');
            }
        });
    });
});

// Format a number with commas
function formatMileageNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
} 

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
