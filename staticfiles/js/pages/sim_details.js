const data_volume = JSON.parse(document.getElementById('data-volume').textContent);
const data_used = JSON.parse(document.getElementById('data-used').textContent);
const sms_volume = JSON.parse(document.getElementById('sms-volume').textContent);
const sms_used = JSON.parse(document.getElementById('sms-used').textContent);
const monthly_use = JSON.parse(document.getElementById("monthly-use").textContent);
const chart_labels = JSON.parse(document.getElementById('chart-labels').textContent);
const label_form = document.getElementById('label-form');
const overlay = document.getElementById('overlay');

const labels = monthly_use.map(item => item.month);
const monthly_data = monthly_use.map(item => item.data_used);
const monthly_sms = monthly_use.map(item => item.sms_used);

function labelFormFunc() {
    const isHidden = label_form.style.display === "none";
    label_form.style.display = isHidden ? "flex" : "none";
    overlay.style.display = isHidden ? "block" : "none";
}

if (overlay) {
    overlay.addEventListener("click", () => {
        if (label_form.style.display !== "none") {
            labelFormFunc();
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

