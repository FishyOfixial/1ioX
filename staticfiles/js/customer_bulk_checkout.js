document.addEventListener("DOMContentLoaded", function () {
    const bulkForm = document.getElementById("cpBulkForm");
    const bulkActions = document.getElementById("cpBulkActions");
    const selectionText = document.getElementById("cpBulkSelectionText");
    const totalAmount = document.getElementById("cpBulkTotalAmount");
    const planSelect = document.getElementById("cpBulkPlan");

    if (!bulkForm || !bulkActions || !selectionText || !totalAmount || !planSelect) {
        return;
    }

    const simCheckboxes = Array.from(bulkForm.querySelectorAll(".cp-bulk-checkbox"));

    function getSelectedCount() {
        return simCheckboxes.filter(function (checkbox) {
            return checkbox.checked;
        }).length;
    }

    function getSelectedPlanPrice() {
        const selectedOption = planSelect.options[planSelect.selectedIndex];
        if (!selectedOption) {
            return 0;
        }
        const price = parseFloat(selectedOption.dataset.price || "0");
        return Number.isFinite(price) ? price : 0;
    }

    function renderBulkState() {
        const selectedCount = getSelectedCount();
        const selectedPlanPrice = getSelectedPlanPrice();
        const total = selectedCount * selectedPlanPrice;

        if (selectedCount > 0) {
            bulkActions.classList.add("is-visible");
            const template = selectionText.dataset.selectedTemplate || "{count} SIM(s) selected";
            selectionText.textContent = template.replace("{count}", String(selectedCount));
        } else {
            bulkActions.classList.remove("is-visible");
            selectionText.textContent = selectionText.dataset.defaultText || selectionText.textContent;
        }

        totalAmount.textContent = "$" + total.toFixed(2);
    }

    selectionText.dataset.defaultText = selectionText.textContent;

    simCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener("change", renderBulkState);
    });

    planSelect.addEventListener("change", renderBulkState);

    bulkForm.addEventListener("submit", function (event) {
        if (getSelectedCount() === 0) {
            event.preventDefault();
        }
    });

    renderBulkState();
});
