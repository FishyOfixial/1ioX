let columnaOrdenActual = null;
let ordenAscendente = true;
let rowsPerPage = 50;
let currentPage = 1;
let totalPages = 1;
let statusIndex = 0;
let statusFilterActual = "ALL";

let tbody, pageInfo, prevBtn, nextBtn, refreshBtn, lengthSelect, activeFilter, inputFilter, exportBtn, bottomBar, selectedCount;
const statusCicle = ["ALL", "ACTIVATED", "DEACTIVATED"];

let allRowsData = [];
let filteredRowsData = [];
const pageCache = new Map();

let date = new Date();
const year = date.getFullYear();
const month = String(date.getMonth() + 1).padStart(2, "0");
const day = String(date.getDate()).padStart(2, "0");
date = `${year}-${month}-${day}`;

document.addEventListener("DOMContentLoaded", () => {
    tbody = document.getElementById("simTbody");
    pageInfo = document.getElementById("pageInfo");
    prevBtn = document.getElementById("prevBtn");
    nextBtn = document.getElementById("nextBtn");
    refreshBtn = document.getElementById("refreshBtn");
    lengthSelect = document.getElementById("rowsPerPage");
    activeFilter = document.getElementById("activeFilter");
    inputFilter = document.getElementById("inputFilter");
    exportBtn = document.getElementById("exportBtn");
    bottomBar = document.getElementById("bottomBar");
    selectedCount = document.getElementById("selectedCount");

    fetchSimsPage(1);

    tbody.addEventListener("dblclick", function (e) {
        const row = e.target.closest("tr");
        if (row) {
            const iccid = row.dataset.iccid;
            window.location.href = `/mis-sim/detalles-sim/${iccid}/`;
        }
    });

    tbody.addEventListener("change", function (e) {
        if (e.target.classList.contains("rowCheckbox")) {
            const row = e.target.closest("tr");
            row.classList.toggle("selected", e.target.checked);
            actualizarBottomBar();
        }
    });

    document.getElementById("statusHeader").addEventListener("click", () => {
        statusIndex = (statusIndex + 1) % statusCicle.length;
        filterByStatus(statusCicle[statusIndex]);
    });

    lengthSelect.addEventListener("change", () => {
        rowsPerPage = parseInt(lengthSelect.value, 10);
        clearPageCache();
        fetchSimsPage(1);
    });

    prevBtn.addEventListener("click", () => {
        if (currentPage > 1) fetchSimsPage(currentPage - 1);
    });

    nextBtn.addEventListener("click", () => {
        if (currentPage < totalPages) fetchSimsPage(currentPage + 1);
    });

    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            clearPageCache();
            fetchSimsPage(currentPage);
        });
    }

    document.getElementById("selectAll").addEventListener("change", function () {
        const checkboxes = tbody.querySelectorAll(".rowCheckbox");
        checkboxes.forEach(cb => {
            const row = cb.closest("tr");
            const visible = row.style.display !== "none";
            if (!visible) return;
            cb.checked = this.checked;
            row.classList.toggle("selected", this.checked);
        });
        actualizarBottomBar();
    });

    activeFilter.addEventListener("change", () => {
        filterPlaceholder();
        filtrarTabla();
    });

    inputFilter.addEventListener("input", filtrarTabla);

    document.getElementById("activateSIMStatus").addEventListener("click", () => {
        enviarFormularioSIM("Enabled");
    });

    document.getElementById("deactivateSIMStatus").addEventListener("click", () => {
        enviarFormularioSIM("Disabled");
    });

    exportBtn.addEventListener("click", exportarCSV);

    const fileInput = document.getElementById("iccidFile");
    document.getElementById("uploadTrigger").addEventListener("click", () => {
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
                cb.closest("tr").classList.toggle("selected", cb.checked);
            });

            actualizarBottomBar();
            fileInput.value = "";
        };
        lector.readAsText(archivo);
    });

    document.getElementById("assignSIMsForm").addEventListener("submit", function () {
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
});

function getPageCacheKey(page) {
    return `${rowsPerPage}:${page}`;
}

function clearPageCache() {
    pageCache.clear();
    allRowsData = [];
    filteredRowsData = [];
    currentPage = 1;
    totalPages = 1;
    if (tbody) tbody.innerHTML = "";
}

function buildRowsForCurrentPage(pageKey) {
    tbody.querySelectorAll(`tr[data-page-key="${pageKey}"]`).forEach(row => row.remove());

    filteredRowsData.forEach(row => {
        const tr = document.createElement("tr");
        tr.dataset.pageKey = pageKey;
        tr.dataset.label = (row.label || "None").toLowerCase();
        tr.dataset.enable = row.isEnable;
        tr.dataset.iccid = row.iccid;
        tr.dataset.distribuidor = row.distribuidor;
        tr.dataset.revendedor = row.revendedor;
        tr.dataset.cliente = row.cliente;
        tr.dataset.whatsapp = row.whatsapp;
        tr.dataset.vehicle = row.vehicle;

        tr.innerHTML = `
            <td><input type="checkbox" class="rowCheckbox" data-iccid="${row.iccid}" data-label="${row.label}"></td>
            <td>
                ${row.isEnable === "Enabled" ? `<span title="Activada">&#9989;</span>` :
                row.isEnable === "Disabled" ? `<span title="Desactivada">&#10060;</span>` :
                    row.isEnable}
            </td>
            <td>
                ${row.status === "ONLINE" ? `<span class="status-circle online" title="Online"></span>` :
                row.status === "OFFLINE" ? `<span class="status-circle offline" title="Offline"></span>` :
                    row.status === "ATTACHED" ? `<span class="status-circle attached" title="Attached"></span>` :
                        `<span class="status-circle" style="background-color: gray;" title="${row.status}"></span>`}
            </td>
            <td>${row.iccid}</td>
            <td>${row.imei || "None"}</td>
            <td>${row.label || "None"}</td>
            <td>${parseFloat(row.volume).toFixed(2)}</td>
        `;

        tbody.appendChild(tr);
    });
}

function renderTable(forceRebuild = false) {
    const pageKey = getPageCacheKey(currentPage);

    tbody.querySelectorAll("tr").forEach(row => {
        row.style.display = "none";
    });

    const existingRows = tbody.querySelectorAll(`tr[data-page-key="${pageKey}"]`);
    if (forceRebuild || existingRows.length === 0) {
        buildRowsForCurrentPage(pageKey);
    }

    tbody.querySelectorAll(`tr[data-page-key="${pageKey}"]`).forEach(row => {
        row.style.display = "";
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
    renderTable(true);
}

function showPage(page) {
    fetchSimsPage(page);
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
    inputFilter.placeholder = activeFilter.value;
}

function filtrarTabla() {
    const filterText = inputFilter.value.toLowerCase().trim();
    const filterValue = activeFilter.value.toLowerCase().trim();

    filteredRowsData = allRowsData.filter(row => {
        const valorTexto = (row[filterValue] || "None").toLowerCase();
        const estadoSIM = row.isEnable.toLowerCase();
        const coincideTexto = valorTexto.includes(filterText);
        const coincideEstado =
            statusFilterActual === "ALL" ||
            (statusFilterActual === "ACTIVATED" && estadoSIM === "enabled") ||
            (statusFilterActual === "DEACTIVATED" && estadoSIM === "disabled");
        return coincideTexto && coincideEstado;
    });

    renderTable(true);
}

function hayFiltroActivo() {
    return inputFilter.value.trim() !== "" || statusFilterActual !== "ALL";
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

    tbody.querySelectorAll("tr").forEach(row => {
        if (row.offsetParent === null) return;
        const cells = row.querySelectorAll("td");
        const estado = getCellTitleOrText(cells[1]);
        const session = getCellTitleOrText(cells[2]);
        const iccid = cells[3]?.innerText.trim();
        const volumen = cells[6]?.innerText.trim();
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

function getCellTitleOrText(cell) {
    if (!cell) return "";
    const span = cell.querySelector("span[title]");
    if (span) return span.getAttribute("title").trim();
    return cell.innerText.trim();
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
    const safeTotalPages = Math.max(1, totalPages);
    pageInfo.textContent = `Pagina ${currentPage} de ${safeTotalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === safeTotalPages;
}

function fetchSimsPage(page = 1) {
    const cacheKey = getPageCacheKey(page);
    const cached = pageCache.get(cacheKey);

    if (cached) {
        allRowsData = cached.rows || [];
        filteredRowsData = [...allRowsData];
        currentPage = cached.page || page;
        totalPages = cached.total_pages || totalPages;

        if (hayFiltroActivo()) {
            filtrarTabla();
        } else {
            renderTable(false);
        }
        filterPlaceholder();
        return;
    }

    const params = new URLSearchParams({
        page: String(page),
        per_page: String(rowsPerPage),
    });

    fetch(`/get-sims-data/?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
            const payload = {
                rows: data.rows || [],
                page: data.page || page,
                total_pages: data.total_pages || 1,
                total_count: data.total_count || 0,
            };

            pageCache.set(getPageCacheKey(payload.page), payload);

            allRowsData = payload.rows;
            filteredRowsData = [...allRowsData];
            currentPage = payload.page;
            totalPages = payload.total_pages;

            if (hayFiltroActivo()) {
                filtrarTabla();
            } else {
                renderTable(true);
            }
            filterPlaceholder();
        })
        .catch(() => {
            allRowsData = [];
            filteredRowsData = [];
            currentPage = 1;
            totalPages = 1;
            renderTable(true);
        });
}
