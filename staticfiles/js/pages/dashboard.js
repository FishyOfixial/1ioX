const activadas = JSON.parse(document.getElementById('activadas-data').textContent);
const desactivadas = JSON.parse(document.getElementById('desactivadas-data').textContent);
const data_suficiente = JSON.parse(document.getElementById('data-suficiente-data').textContent);
const data_bajo = JSON.parse(document.getElementById('data-bajo-data').textContent);
const data_sin_volumen = JSON.parse(document.getElementById('data-sin-volumen-data').textContent);
const sms_suficiente = JSON.parse(document.getElementById('sms-suficiente-data').textContent);
const sms_bajo = JSON.parse(document.getElementById('sms-bajo-data').textContent);
const sms_sin_volumen = JSON.parse(document.getElementById('sms-sin-volumen-data').textContent);
const month_label = JSON.parse(document.getElementById('month-label-data').textContent);
const data_usage = JSON.parse(document.getElementById('data-usage-data').textContent);
const data_sms = JSON.parse(document.getElementById('data-sms-data').textContent);
const top_usage_data = JSON.parse(document.getElementById('top-usage-data').textContent);
const top_sms_data = JSON.parse(document.getElementById('top-usage-sms').textContent);
const data_usage_txt = JSON.parse(document.getElementById('data-usage-txt').textContent);
const sms_usage_txt = JSON.parse(document.getElementById('sms-usage-txt').textContent);
const data_volume_txt = JSON.parse(document.getElementById('data-volume').textContent);
const sms_volume_txt = JSON.parse(document.getElementById('sms-volume').textContent);
const volume_label = JSON.parse(document.getElementById('volume-label').textContent);
const sim_status_txt = JSON.parse(document.getElementById('sim-status-txt').textContent);
const sim_status_label = JSON.parse(document.getElementById('sim-status-label').textContent);

let columnaOrdenActual = null;
let ordenAscendente = true;

function ordenarTabla(columna, tipo, thElement) {
    const tabla = document.getElementById("orderTable");
    const filas = Array.from(tabla.tBodies[0].rows);

    if (columna === columnaOrdenActual) {
        ordenAscendente = !ordenAscendente;
    } else {
        ordenAscendente = true;
        columnaOrdenActual = columna;
    }

    filas.sort((a, b) => {
        let valorA = a.cells[columna].textContent.trim();
        let valorB = b.cells[columna].textContent.trim();

        if (tipo === 'numero') {
            valorA = parseFloat(valorA.replace(/[^\d.-]/g, '')) || 0;
            valorB = parseFloat(valorB.replace(/[^\d.-]/g, '')) || 0;
        } else if (tipo === 'fecha') {
            valorA = new Date(valorA);
            valorB = new Date(valorB);
        } else {
            valorA = valorA.toLowerCase();
            valorB = valorB.toLowerCase();
        }

        if (valorA < valorB) return ordenAscendente ? -1 : 1;
        if (valorA > valorB) return ordenAscendente ? 1 : -1;
        return 0;
    });

    document.querySelectorAll('th .flecha').forEach(f => f.textContent = '');
    thElement.querySelector('.flecha').textContent = ordenAscendente ? '▲' : '▼';

    filas.forEach(fila => tabla.tBodies[0].appendChild(fila));
}

function showDataCard(label, iccidOrArray) {
    const card = document.getElementById('topDataUsage');

    let htmlContent = `<button class="close-btn" onclick="closeDataCard()">✖</button>`;
    htmlContent += `<h3>Consumo alto en: ${label}</h3>`;

    if (iccidOrArray.length === 0) {
        htmlContent += `<p>No hay SIMs que hayan consumido más del 75% del límite establecido.</p>`;
    } else {
        htmlContent += `<ul>`;
        iccidOrArray.forEach(({ iccid, data_used }) => {
            htmlContent += `<li><strong>ICCID:</strong> ${iccid} — <strong>Datos usados:</strong> ${data_used.toFixed(2)} MB</li>`;
        });
        htmlContent += `</ul>`;
    }

    card.innerHTML = htmlContent;
    card.style.display = 'block';
    card.classList.add('show');
}

function closeDataCard() {
    const card = document.getElementById('topDataUsage');
    card.classList.remove('show');
    setTimeout(() => {
        card.style.display = 'none';
    }, 300);
}

function showSMSCard(label, iccidOrArray) {
    const card = document.getElementById('topSMSUsage');

    let htmlContent = `<button class="close-btn" onclick="closeSMSCard()">✖</button>`;
    htmlContent += `<h3>Consumo alto en: ${label}</h3>`;

    if (iccidOrArray.length === 0) {
        htmlContent += `<p>No hay SIMs que hayan consumido más de 20 SMS.</p>`;
    } else {
        htmlContent += `<ul>`;
        iccidOrArray.forEach(({ iccid, sms_used }) => {
            htmlContent += `<li><strong>ICCID:</strong> ${iccid} — <strong>SMS usados:</strong> ${sms_used}</li>`;
        });
        htmlContent += `</ul>`;
    }

    card.innerHTML = htmlContent;
    card.style.display = 'block';
    card.classList.add('show');
}

function closeSMSCard() {
    const card = document.getElementById('topSMSUsage');
    card.classList.remove('show');
    setTimeout(() => {
        card.style.display = 'none';
    }, 300);
}

document.addEventListener("DOMContentLoaded", function () {
    const rows = document.querySelectorAll('#orderTable tbody tr');

    rows.forEach(row => {
        row.addEventListener("dblclick", function () {
            const order_number = this.dataset.order;
            window.location.href = `/detalles-orden/${order_number}/`;
        });
    });
});
