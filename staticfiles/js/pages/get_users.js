const distribuidor = document.querySelectorAll('#distribuidorTable tbody tr');
const revendedor = document.querySelectorAll('#revendedorTable tbody tr');
const cliente = document.querySelectorAll('#clienteTable tbody tr');

let columnaOrdenActual = null;
let ordenAscendente = true;

function createDistribuidor() {
    window.location.href = 'crear-distribuidor/'
}

function createRevendedor() {
    window.location.href = 'crear-revendedor/'
}

function createCliente() {
    window.location.href = 'crear-cliente/'
}

window.addEventListener("DOMContentLoaded", () => {

    distribuidor.forEach(row => {
        row.addEventListener("dblclick", function () {
            const user_id = this.dataset.id
            const type = this.dataset.type;

            window.location.href = `detalles-${type}/${user_id}`
        })
    })

    revendedor.forEach(row => {
        row.addEventListener("dblclick", function () {
            const user_id = this.dataset.id
            const type = this.dataset.type;

            window.location.href = `detalles-${type}/${user_id}`
        })
    })

    cliente.forEach(row => {
        row.addEventListener("dblclick", function () {
            const user_id = this.dataset.id
            const type = this.dataset.type;

            window.location.href = `detalles-${type}/${user_id}`
        })
    })

})

const filterDistribuidor = document.getElementById('filterDistribuidor');
const filterRevendedor = document.getElementById('filterRevendedor');
const filterCliente = document.getElementById('filterCliente');

function filtrarTabla() {
    const filterDisText = filterDistribuidor.value.toLowerCase().trim();
    const filterRevText = filterRevendedor.value.toLowerCase().trim();
    const filterCliText = filterCliente.value.toLowerCase().trim();

    distribuidor.forEach(row => {
        const valorTexto = row.dataset['name']?.toLowerCase() || "";

        const coincideTexto = valorTexto.includes(filterDisText);

        if (coincideTexto) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });

    revendedor.forEach(row => {
        const valorTexto = row.dataset['name']?.toLowerCase() || "";

        const coincideTexto = valorTexto.includes(filterRevText);

        if (coincideTexto) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });

    cliente.forEach(row => {
        const valorTexto = row.dataset['name']?.toLowerCase() || "";

        const coincideTexto = valorTexto.includes(filterCliText);

        if (coincideTexto) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}

filterDistribuidor.addEventListener("input", filtrarTabla)
filterRevendedor.addEventListener("input", filtrarTabla)
filterCliente.addEventListener("input", filtrarTabla)

function ordenarTabla(tabla, columna, tipo, thElement) {
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