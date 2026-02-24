let columnaOrdenActual = null;
let ordenAscendente = true;
let rowsPerPage = 50;
let currentPage = 1;
let statusIndex = 0;
let statusFilterActual = "ALL";
let mbSortAsc = true;

let tbody, pageInfo, prevBtn, nextBtn, refreshBtn, lengthSelect, inputFilter, exportBtn, bottomBar, selectedCount;
const statusCicle = ["ALL", "ACTIVATED", "DEACTIVATED"];

let allRowsData = [];
let filteredRowsData = [];
let loadedIccids = new Set();

let nextOffset = 0;
let hasMoreData = true;
let isBackgroundLoading = false;
let totalCount = 0;
let sessionLabels = {
    ONLINE: "Online",
    OFFLINE: "Offline",
    ATTACHED: "Attached",
};

const INITIAL_CHUNK_SIZE = 50;
const BACKGROUND_CHUNK_SIZE = 100;

document.addEventListener("DOMContentLoaded", () => {
    tbody = document.getElementById("simTbody");
    pageInfo = document.getElementById("pageInfo");
    prevBtn = document.getElementById("prevBtn");
    nextBtn = document.getElementById("nextBtn");
    refreshBtn = document.getElementById("refreshBtn");
    lengthSelect = document.getElementById("rowsPerPage");
    inputFilter = document.getElementById("inputFilter");
    exportBtn = document.getElementById("exportBtn");
    bottomBar = document.getElementById("bottomBar");
    selectedCount = document.getElementById("selectedCount");
    sessionLabels = {
        ONLINE: tbody.dataset.sessionOn || "Online",
        OFFLINE: tbody.dataset.sessionOff || "Offline",
        ATTACHED: tbody.dataset.sessionAt || "Attached",
    };

    const requiredNodes = [tbody, pageInfo, prevBtn, nextBtn, lengthSelect, inputFilter, exportBtn, bottomBar, selectedCount];
    if (requiredNodes.some(node => !node)) {
        console.error("get_sims.js: faltan elementos del DOM requeridos, se cancela inicializacion.");
        return;
    }

    loadInitialAndBackground();

    tbody.addEventListener("dblclick", function (e) {
        const row = e.target.closest(".sim-card");
        if (row) {
            const iccid = row.dataset.iccid;
            window.location.href = `/mis-sim/detalles-sim/${iccid}/`;
        }
    });

    tbody.addEventListener("change", function (e) {
        if (e.target.classList.contains("rowCheckbox")) {
            const row = e.target.closest(".sim-card");
            row.classList.toggle("selected", e.target.checked);
            actualizarBottomBar();
        }
    });

    const statusHeader = document.getElementById("statusHeader");
    if (statusHeader) {
        statusHeader.addEventListener("click", () => {
            statusIndex = (statusIndex + 1) % statusCicle.length;
            filterByStatus(statusCicle[statusIndex]);
        });
    }
    const sortDataBtn = document.getElementById("sortDataBtn");
    if (sortDataBtn) {
        sortDataBtn.addEventListener("click", () => {
            mbSortAsc = !mbSortAsc;
            filteredRowsData.sort((a, b) => {
                const volA = parseFloat(a.volume) || 0;
                const volB = parseFloat(b.volume) || 0;
                return mbSortAsc ? volA - volB : volB - volA;
            });
            renderTable();
        });
    }

    lengthSelect.addEventListener("change", () => {
        rowsPerPage = parseInt(lengthSelect.value, 10);
        showPage(1);
    });

    prevBtn.addEventListener("click", () => {
        if (currentPage > 1) showPage(currentPage - 1);
    });

    nextBtn.addEventListener("click", () => {
        const totalPages = getTotalPages();
        if (currentPage < totalPages) showPage(currentPage + 1);
    });

    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            resetDataAndReload();
        });
    }

    const selectAll = document.getElementById("selectAll");
    if (selectAll) {
        selectAll.addEventListener("change", function () {
            const checkboxes = tbody.querySelectorAll(".rowCheckbox");
            checkboxes.forEach(cb => {
                const row = cb.closest(".sim-card");
                cb.checked = this.checked;
                row.classList.toggle("selected", this.checked);
            });
            actualizarBottomBar();
        });
    }

    inputFilter.addEventListener("input", filtrarTabla);

    const activateSIMStatus = document.getElementById("activateSIMStatus");
    const deactivateSIMStatus = document.getElementById("deactivateSIMStatus");
    if (activateSIMStatus) {
        activateSIMStatus.addEventListener("click", () => {
            enviarFormularioSIM("Enabled");
        });
    }
    if (deactivateSIMStatus) {
        deactivateSIMStatus.addEventListener("click", () => {
            enviarFormularioSIM("Disabled");
        });
    }

    exportBtn.addEventListener("click", exportarCSV);

    const fileInput = document.getElementById("iccidFile");
    const uploadTrigger = document.getElementById("uploadTrigger");
    if (fileInput && uploadTrigger) {
        uploadTrigger.addEventListener("click", () => {
            fileInput.click();
        });

        fileInput.addEventListener("change", function () {
            const archivo = this.files[0];
            if (!archivo) return;
            const lector = new FileReader();
            lector.onload = function (e) {
                const iccidsDesdeArchivo = e.target.result
                    .split("\n")
                    .map(linea => linea.trim())
                    .filter(linea => linea.length > 0);

                tbody.querySelectorAll(".rowCheckbox").forEach(cb => {
                    const iccid = cb.dataset.iccid;
                    cb.checked = iccidsDesdeArchivo.includes(iccid);
                    cb.closest(".sim-card").classList.toggle("selected", cb.checked);
                });

                actualizarBottomBar();
                fileInput.value = "";
            };
            lector.readAsText(archivo);
        });
    }

    const assignSIMsForm = document.getElementById("assignSIMsForm");
    if (assignSIMsForm) {
        assignSIMsForm.addEventListener("submit", function () {
            const contenedorInputs = document.getElementById("inputs-sims");
            contenedorInputs.innerHTML = "";
            const selectedData = getSelectedICCID();
            selectedData.iccids.forEach(iccid => {
                const input = document.createElement("input");
                input.type = "hidden";
                input.name = "sim_ids";
                input.value = iccid;
                contenedorInputs.appendChild(input);
            });
        });
    }
});

async function loadInitialAndBackground() {
    const initial = await fetchSimsChunk(0, INITIAL_CHUNK_SIZE);
    if (!initial) return;

    mergeRows(initial.rows || []);
    totalCount = initial.total_count || allRowsData.length;
    nextOffset = initial.next_offset || allRowsData.length;
    hasMoreData = Boolean(initial.has_more);

    applyFiltersAndRender(false);
    filterPlaceholder();

    runBackgroundLoad();
}

async function runBackgroundLoad() {
    if (isBackgroundLoading) return;
    isBackgroundLoading = true;

    if (!hasMoreData || nextOffset >= totalCount) {
        isBackgroundLoading = false;
        return;
    }

    const offsets = [];
    for (let offset = nextOffset; offset < totalCount; offset += BACKGROUND_CHUNK_SIZE) {
        offsets.push(offset);
    }

    const settled = await Promise.allSettled(
        offsets.map(offset =>
            fetchSimsChunk(offset, BACKGROUND_CHUNK_SIZE).then(data => ({ offset, data }))
        )
    );

    const successful = settled
        .filter(r => r.status === "fulfilled" && r.value && r.value.data)
        .map(r => r.value)
        .sort((a, b) => a.offset - b.offset);

    successful.forEach(result => {
        mergeRows(result.data.rows || []);
    });

    nextOffset = totalCount;
    hasMoreData = loadedIccids.size < totalCount;
    applyFiltersAndRender(true);

    isBackgroundLoading = false;
}

function fetchSimsChunk(offset, limit) {
    const params = new URLSearchParams({
        offset: String(offset),
        limit: String(limit),
    });

    return fetch(`/get-sims-data/?${params.toString()}`)
        .then(res => res.json())
        .catch(() => null);
}

function mergeRows(rows) {
    rows.forEach(row => {
        if (!loadedIccids.has(row.iccid)) {
            loadedIccids.add(row.iccid);
            allRowsData.push(row);
        }
    });
}

function getTotalPages() {
    return Math.max(1, Math.ceil(filteredRowsData.length / rowsPerPage));
}

function renderTable() {
    tbody.innerHTML = "";

    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const pageRows = filteredRowsData.slice(start, end);

    pageRows.forEach(row => {
        const card = document.createElement("article");
        card.className = "sim-card";
        if (row.isEnable === "Enabled") {
            card.classList.add("sim-card-enabled");
        } else if (row.isEnable === "Disabled") {
            card.classList.add("sim-card-disabled");
        }
        card.dataset.label = (row.label || "None").toLowerCase();
        card.dataset.enable = row.isEnable;
        card.dataset.iccid = row.iccid;
        card.dataset.distribuidor = row.distribuidor;
        card.dataset.revendedor = row.revendedor;
        card.dataset.cliente = row.cliente;
        card.dataset.whatsapp = row.whatsapp;
        card.dataset.vehicle = row.vehicle;
        card.dataset.session = row.status || "UNKNOWN";
        card.dataset.volume = (parseFloat(row.volume) || 0).toFixed(2);

        const simStateLabel = row.isEnable === "Enabled" ? "Activada" : row.isEnable === "Disabled" ? "Desactivada" : row.isEnable;
        const sessionTitle = sessionLabels[row.status] || row.status;
        const sessionDotClass = row.status === "ONLINE" ? "online" : row.status === "OFFLINE" ? "offline" : row.status === "ATTACHED" ? "attached" : "";

        card.innerHTML = `
            <div class="sim-card-head">
                <label class="card-check"><input type="checkbox" class="rowCheckbox" data-iccid="${row.iccid}" data-label="${row.label || ""}"></label>
                <h3>${row.iccid}</h3>
            </div>
            <dl class="sim-card-data">
                <div><dt>Estado</dt><dd><span class="sim-state-chip">${simStateLabel}</span></dd></div>
                <div><dt>Sesion</dt><dd><span class="session-chip"><span class="status-circle ${sessionDotClass}" title="${sessionTitle}"></span> ${sessionTitle}</span></dd></div>
                <div><dt>IMEI</dt><dd>${row.imei || "None"}</dd></div>
                <div><dt>Etiqueta</dt><dd>${row.label || "None"}</dd></div>
                <div><dt>MB disponibles</dt><dd>${card.dataset.volume}</dd></div>
            </dl>
        `;

        tbody.appendChild(card);
    });

    actualizarBottomBar();
    updatePageInfo();
}

function filterByStatus(status) {
    statusFilterActual = status;
    filtrarTabla();
}

function ordenarTabla(columna, tipo, thElement) {
    if (columna === columnaOrdenActual) ordenAscendente = !ordenAscendente;
    else {
        ordenAscendente = true;
        columnaOrdenActual = columna;
    }

    filteredRowsData.sort((a, b) => {
        let valorA;
        let valorB;
        switch (columna) {
            case 6:
                valorA = parseFloat(a.volume) || 0;
                valorB = parseFloat(b.volume) || 0;
                break;
            default:
                valorA = "";
                valorB = "";
        }
        if (tipo === "numero") {
            valorA = parseFloat(valorA) || 0;
            valorB = parseFloat(valorB) || 0;
        }
        if (valorA < valorB) return ordenAscendente ? -1 : 1;
        if (valorA > valorB) return ordenAscendente ? 1 : -1;
        return 0;
    });

    document.querySelectorAll("th .flecha").forEach(f => {
        f.textContent = "";
    });
    thElement.querySelector(".flecha").textContent = ordenAscendente ? "^" : "v";
    renderTable();
}

function showPage(page) {
    currentPage = page;
    renderTable();
}

function getSelectedICCID() {
    const selected = [];
    const label = [];
    tbody.querySelectorAll(".rowCheckbox:checked").forEach(cb => {
        selected.push(cb.dataset.iccid);
        label.push(cb.dataset.label);
    });
    return { count: selected.length, iccids: selected, labels: label };
}

function filterPlaceholder() {
    if (!inputFilter) return;
    inputFilter.placeholder = inputFilter.dataset.placeholder || "Buscar por ICCID o etiqueta";
}

function applyFiltersAndRender(keepPage) {
    const filterText = inputFilter ? inputFilter.value.toLowerCase().trim() : "";

    filteredRowsData = allRowsData.filter(row => {
        const iccid = (row.iccid || "").toLowerCase();
        const label = (row.label || "").toLowerCase();
        const estadoSIM = row.isEnable.toLowerCase();
        const coincideTexto =
            filterText === "" ||
            iccid.includes(filterText) ||
            label.includes(filterText);
        const coincideEstado =
            statusFilterActual === "ALL" ||
            (statusFilterActual === "ACTIVATED" && estadoSIM === "enabled") ||
            (statusFilterActual === "DEACTIVATED" && estadoSIM === "disabled");
        return coincideTexto && coincideEstado;
    });

    if (keepPage) {
        currentPage = Math.min(currentPage, getTotalPages());
    } else {
        currentPage = 1;
    }

    renderTable();
}

function filtrarTabla() {
    applyFiltersAndRender(false);
}

function hayFiltroActivo() {
    const hasTextFilter = inputFilter ? inputFilter.value.trim() !== "" : false;
    return hasTextFilter || statusFilterActual !== "ALL";
}

function actualizarBottomBar() {
    const { count } = getSelectedICCID();
    if (count > 0) {
        bottomBar.style.display = "";
        bottomBar.classList.add("appear");
        bottomBar.classList.remove("disappear");
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

function exportarCSV() {
    const data = [];
    data.push([
        "Estado", "Session", "ICCID", "DISTRIBUIDOR", "REVENDEDOR", "CLIENTE", "whatsapp cliente", "Vehiculo", "MB Disponibles"
    ]);

    tbody.querySelectorAll(".sim-card").forEach(row => {
        const estado = row.dataset.enable === "Enabled" ? "Activada" : row.dataset.enable === "Disabled" ? "Desactivada" : (row.dataset.enable || "");
        const session = row.dataset.session || "";
        const iccid = row.dataset.iccid || "";
        const volumen = row.dataset.volume || "";
        const distribuidor = row.dataset.distribuidor || "";
        const revendedor = row.dataset.revendedor || "";
        const cliente = row.dataset.cliente || "";
        const whatsapp = row.dataset.whatsapp || "";
        const vehicle = row.dataset.vehicle || "";
        data.push([estado, session, iccid, distribuidor, revendedor, cliente, whatsapp, vehicle, volumen]);
    });

    const now = new Date();
    const filename = `SIM_Info_${String(now.getDate()).padStart(2, "0")}-${String(now.getMonth() + 1).padStart(2, "0")}-${now.getFullYear()}_${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}.xlsx`;
    const worksheet = XLSX.utils.aoa_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet);
    XLSX.writeFile(workbook, filename);
}

function toggleAssignationForm() {
    const form = document.getElementById("assignation-div");
    const overlay = document.getElementById("overlay");
    if (form.style.display === "none") {
        overlay.style.display = form.style.display = "flex";
        document.getElementById("overlay-text").textContent = "";
    } else {
        overlay.style.display = form.style.display = "none";
        document.getElementById("overlay-text").textContent = "Procesando, por favor espera...";
    }
}

function updatePageInfo() {
    const totalPages = getTotalPages();
    pageInfo.textContent = `Pagina ${currentPage} de ${totalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
}

function resetDataAndReload() {
    allRowsData = [];
    filteredRowsData = [];
    loadedIccids = new Set();
    nextOffset = 0;
    hasMoreData = true;
    isBackgroundLoading = false;
    totalCount = 0;
    currentPage = 1;
    renderTable();
    loadInitialAndBackground();
}
