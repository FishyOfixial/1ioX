const data_volume = JSON.parse(document.getElementById('data-volume').textContent);
const data_used = JSON.parse(document.getElementById('data-used').textContent);
const sms_volume = JSON.parse(document.getElementById('sms-volume').textContent);
const sms_used = JSON.parse(document.getElementById('sms-used').textContent);
const monthly_use = JSON.parse(document.getElementById("monthly-use").textContent);
const chart_labels = JSON.parse(document.getElementById('chart-labels').textContent);
const label_form = document.getElementById('label-form');
const overlay = document.getElementById('overlay')
const inputs = label_form.querySelectorAll("input")

const labels = monthly_use.map(item => item.month);
const monthly_data = monthly_use.map(item => item.data_used);
const monthly_sms = monthly_use.map(item => item.sms_used);


function labelFormFunc() {
    if (label_form.style.display === "none") {
        label_form.style.display = "flex"
        overlay.style.display = "block"
    }
    else {
        label_form.style.display = "none"
        overlay.style.display = "none"

        inputs.forEach(input => {
            input.value = ""
        })
    }
}

const dragHandle = document.getElementById('drag')
let offsetX = 0, offsetY = 0, isDown = false;

dragHandle.addEventListener("mousedown", (e) => {
    isDown = true;
    offsetX = e.clientX - label_form.offsetLeft;
    offsetY = e.clientY = label_form.offsetTop;
});

document.addEventListener("mouseup", () => {
    isDown = false;
})

document.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    label_form.style.left = (e.clientX - offsetX) + "px";
    label_form.style.top = (e.clientY - offsetY) + "px";
})

document.addEventListener("DOMContentLoaded", () => {
    const locationBtn = document.getElementById("locationBtn");
    const iccid = locationBtn.getAttribute('data-iccid')

    fetch(`/get-location/${iccid}/`)
        .then(response => {
            if (!response.ok) throw new Error("Ubicación no disponible");
            return response.json();
        })
        .then(data => {
            if (data.latitude && data.longitude) {
                locationBtn.disabled = false;
                locationBtn.style.pointerEvents = 'auto';
                locationBtn.style.opacity = '1';
                locationBtn.setAttribute("data-url", `https://www.google.com/maps?q=${data.latitude},${data.longitude}`);
                const date = new Date(data.sample_time);
                const formatted = date.toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                locationBtn.textContent = `Ver ubicación - ${formatted}`;
            } else {
                locationBtn.textContent = "Ubicación no disponible";
            }
        })
        .catch(() => {
            locationBtn.textContent = "Error cargando ubicación";
        });
});

function goTo(elem, openInNewTab = false) {
    const url = elem.getAttribute("data-url");
    if (!url) return;
    if (openInNewTab) {
        window.open(url, '_blank');
    } else {
        window.location.href = url;
    }
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