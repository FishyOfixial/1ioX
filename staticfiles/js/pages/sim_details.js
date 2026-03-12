const data_volume = JSON.parse(document.getElementById('data-volume').textContent);
const data_used = JSON.parse(document.getElementById('data-used').textContent);
const sms_volume = JSON.parse(document.getElementById('sms-volume').textContent);
const sms_used = JSON.parse(document.getElementById('sms-used').textContent);
const monthly_use = JSON.parse(document.getElementById("monthly-use").textContent);
const chart_labels = JSON.parse(document.getElementById('chart-labels').textContent);
const labelForm = document.getElementById('label-form');

const labels = monthly_use.map(item => item.month);
const monthly_data = monthly_use.map(item => item.data_used);
const monthly_sms = monthly_use.map(item => item.sms_used);
const clientSearch = document.querySelector('[data-client-search]');
const clientSelect = document.querySelector('[data-client-select]');

function setFormOpen(isOpen) {
    if (!labelForm) {
        return;
    }

    labelForm.style.display = isOpen ? "flex" : "none";
}

function labelFormFunc() {
    if (!labelForm) {
        return;
    }

    const isHidden = labelForm.style.display === "none" || !labelForm.style.display;
    setFormOpen(isHidden);
}

if (labelForm) {
    labelForm.addEventListener("click", (event) => {
        if (event.target === labelForm) {
            setFormOpen(false);
        }
    });
}

function onResizeThreshold(threshold, callback) {
    let wasBelow = window.innerWidth < threshold;
    window.addEventListener('resize', () => {
        const isBelow = window.innerWidth < threshold;
        if (wasBelow !== isBelow) {
            callback(isBelow);
            wasBelow = isBelow;
        }
    });
}

onResizeThreshold(900, (isBelow) => {
    const key = 'resizeReloadDone';
    const lastState = sessionStorage.getItem(key);

    if (lastState !== String(isBelow)) {
        sessionStorage.setItem(key, String(isBelow));
        window.location.reload();
    }
});

if (clientSearch && clientSelect) {
    const options = Array.from(clientSelect.options);
    clientSearch.addEventListener("input", () => {
        const term = clientSearch.value.toLowerCase().trim();
        options.forEach(option => {
            const isPlaceholder = option.value === "" && !option.disabled;
            const isEmptyState = option.value === "" && option.disabled;
            if (isPlaceholder) {
                option.hidden = false;
                return;
            }
            if (isEmptyState) {
                option.hidden = term.length > 0;
                return;
            }
            const text = option.textContent.toLowerCase();
            const matches = term === "" || text.includes(term);
            option.hidden = !matches && !option.selected;
        });
    });
}

