const distribuidor = document.querySelectorAll('#distribuidorTable tbody tr');
const revendedor = document.querySelectorAll('#revendedorTable tbody tr');
const cliente = document.querySelectorAll('#clienteTable tbody tr');

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
    const filterDisText = filterDistribuidor.value.toLowerCase();
    const filterRevText = filterRevendedor.value.toLowerCase()
    const filterCliText = filterCliente.value.toLowerCase()

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