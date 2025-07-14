let columnaOrdenActual = null;
let ordenAscendente = true;
let rowsPerPage = parseInt(document.getElementById('rowsPerPage').value);
let currentPage = 1;
let statusIndex = 0;
let statusFilterActual = "ALL";

const tbody = document.getElementById('simTbody');
const rows = tbody.querySelectorAll('tr');
const pageInfo = document.getElementById('pageInfo');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const refreshBtn = document.getElementById('refreshBtn');
const lengthSelect = document.getElementById('rowsPerPage');
const activeFilter = document.getElementById('activeFilter');
const inputFilter = document.getElementById('inputFilter');
const exportBtn = document.getElementById("exportBtn");
const bottomBar = document.getElementById("bottomBar");
const selectedCount = document.getElementById("selectedCount");
const statusCicle = ["ALL", "ACTIVATED", "DEACTIVATED"];

window.addEventListener("DOMContentLoaded", () => {

    rows.forEach(row => {
        row.addEventListener("dblclick", function () {
            const iccid = this.dataset.iccid;
            window.location.href = `/mis-sim/detalles-sim/${iccid}/`;
        });
    });
});

document.getElementById("statusHeader").addEventListener("click", () => {
    statusIndex = (statusIndex + 1) % statusCicle.length;
    const statusActual = statusCicle[statusIndex];
    filterByStatus(statusActual);
})

function filterByStatus(status) {
    statusFilterActual = status;
    filtrarTabla();
}

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
        }

        if (valorA < valorB) return ordenAscendente ? -1 : 1;
        if (valorA > valorB) return ordenAscendente ? 1 : -1;
        return 0;

    });

    document.querySelectorAll('th .flecha').forEach(f => f.textContent = '');
    thElement.querySelector('.flecha').textContent = ordenAscendente ? '▲' : '▼';

    filas.forEach(fila => tabla.tBodies[0].appendChild(fila));
}

function showPage(page) {
    currentPage = page;
    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    rows.forEach((row, i) => {
        row.style.display = i >= start && i < end ? '' : 'none';
    });

    const totalPages = Math.ceil(rows.length / rowsPerPage);
    pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;

    lengthSelect.disabled = false;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
}

prevBtn.addEventListener('click', () => {
    if (currentPage > 1) showPage(currentPage - 1);
});

nextBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    if (currentPage < totalPages) showPage(currentPage + 1);
});


lengthSelect.addEventListener('change', () => {
    rowsPerPage = parseInt(lengthSelect.value);
    showPage(1);
});


document.querySelectorAll(".rowCheckbox").forEach(cb => {
    cb.addEventListener("change", function () {
        const row = this.closest("tr");

        if (this.checked) {
            row.classList.add("selected");
        } else {
            row.classList.remove("selected");
        }

        actualizarBottomBar();
    });
});

document.getElementById("selectAll").addEventListener("change", function () {
    const checkboxes = document.querySelectorAll(".rowCheckbox");

    checkboxes.forEach(cb => {
        const row = cb.closest("tr")

        if (hayFiltroActivo()) {
            const visible = window.getComputedStyle(row).display !== "none";
            if (!visible) return;
        }

        cb.checked = this.checked;

        if (this.checked) {
            row.classList.add("selected");
        } else {
            row.classList.remove("selected");
        }

        actualizarBottomBar();

    });
});

function getSelectedICCID() {
    const selected = [];
    const label = [];
    document.querySelectorAll(".rowCheckbox:checked").forEach(cb => {
        selected.push(cb.dataset.iccid);
        label.push(cb.dataset.label);
    });
    return {
        count: selected.length,
        iccids: selected,
        labels: label
    }
}

function filterPlaceholder() {
    inputFilter.placeholder = "Buscar por " + activeFilter.value
}

function filtrarTabla() {
    const filterText = inputFilter.value.toLowerCase();
    const filterValue = activeFilter.value.toLowerCase();

    rows.forEach(row => {
        const valorTexto = row.dataset[filterValue]?.toLowerCase() || "";
        const estadoSIM = row.dataset.enable;
        const cb = row.querySelector(".rowCheckbox");

        const coincideTexto = valorTexto.includes(filterText);
        const coincideEstado =
            statusFilterActual === "ALL" ||
            (statusFilterActual === "ACTIVATED" && estadoSIM === "enabled") ||
            (statusFilterActual === "DEACTIVATED" && estadoSIM === "disabled");

        if (coincideTexto && coincideEstado) {
            row.style.display = "";
        } else {
            row.style.display = "none";
            row.classList.remove("selected");
            cb.checked = false;
        }
    });

    if (hayFiltroActivo() || statusFilterActual !== "ALL") {
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        lengthSelect.disabled = true
    } else {
        showPage(1);
    }

    actualizarBottomBar();
}


activeFilter.addEventListener("change", () => {
    filterPlaceholder();
    filtrarTabla();
});

inputFilter.addEventListener("input", filtrarTabla)

function hayFiltroActivo() {
    return inputFilter.value.trim() !== "" || statusFilterActual !== "ALL";
}

function actualizarBottomBar() {
    const { count } = getSelectedICCID()

    if (count > 0) {
        bottomBar.style.display = "";
        bottomBar.classList.add("appear");
        bottomBar.classList.remove("disappear")
        selectedCount.textContent = count;
    } else {
        bottomBar.classList.remove("appear");
        bottomBar.classList.add("disappear");
        setTimeout(() => {
            if (bottomBar.classList.contains("disappear")) {
                bottomBar.style.display = "none";
            }
        }, 300);
    }
}

function enviarFormularioSIM(status) {
    const { iccids, labels } = getSelectedICCID();

    document.getElementById("overlay").style.display = "flex";

    document.getElementById("formStatus").value = status;
    document.getElementById("formICCIDs").value = JSON.stringify(iccids);
    document.getElementById("formLabels").value = JSON.stringify(labels);
    document.getElementById("simStatusForm").submit();
}

document.getElementById("activateSIMStatus").addEventListener("click", () => {
    enviarFormularioSIM("Enabled");
});

document.getElementById("deactivateSIMStatus").addEventListener("click", () => {
    enviarFormularioSIM("Disabled");
});


showPage(1);
filterPlaceholder()
