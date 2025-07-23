let modoEdicion = false;

function toggleEdicion(btn) {
    const inputs = document.querySelectorAll('#editForm input');
    const editBtn = document.getElementById('toggleEditBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const guardarBtn = document.getElementById('guardarBtn');

    if (!modoEdicion) {
        inputs.forEach(input => {
            input.classList.remove('read-only');
            input.readOnly = false;
        });
        editBtn.style.display = 'none';
        cancelBtn.style.display = 'block';
        guardarBtn.classList.remove('hidden');
        modoEdicion = true;
    } else {
        inputs.forEach(input => {
            input.readOnly = true
            input.classList.add('read-only');
        });
        editBtn.style.display = 'block';
        cancelBtn.style.display = 'none';
        guardarBtn.classList.add('hidden');
        modoEdicion = false;
    }
}

function confirmAction(action, isActive = null) {
    const action_form = document.getElementById("action-form");
    const text = document.getElementById('text-form')
    const overlay = document.getElementById('overlay')
    const action_input = document.getElementById("accionInput");

    if (action === 'Cancel') {
        overlay.style.display = "none";
        action_form.style.display = "none";
        return;
    }

    overlay.style.display = 'flex';
    action_form.style.display = 'flex';

    if (action === "Delete") {
        text.innerHTML = "<strong>¿Estás seguro de que deseas eliminar al usuario?</strong><br>Esta acción no se puede deshacer.";
        action_input.value = "delete";
    } else if (action === "Active") {
        const activar = isActive === "False" || isActive === false;
        text.innerHTML = activar
            ? "<strong>¿Estás seguro de que deseas activar al usuario?</strong><br>Esto permitirá que pueda iniciar sesión nuevamente."
            : "<strong>¿Estás seguro de que deseas desactivar al usuario?</strong><br>Esta acción impedirá que inicie sesión.";
        action_input.value = "active"
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const icon = document.getElementById("toggleIcon");
    if (!icon) return;

    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        icon.addEventListener("touchend", (e) => {
            e.preventDefault();
            togglePasswordVisibility();
        });
    } else {
        icon.addEventListener("click", togglePasswordVisibility);
    }

    function togglePasswordVisibility() {
        const text = document.getElementById('passwordText');

        if (icon.alt === "ocultar") {
            icon.src = icon.dataset.view;
            icon.alt = "ver";
            text.style.display = 'none';
        } else {
            icon.src = icon.dataset.close;
            icon.alt = "ocultar";
            text.style.display = 'block';
        }
    }
});