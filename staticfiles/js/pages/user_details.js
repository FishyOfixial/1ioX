let modoEdicion = false;

function toggleEdicion() {
    const inputs = document.querySelectorAll('#editForm input');
    const btn = document.getElementById('toggleEditBtn');
    const guardarBtn = document.getElementById('guardarBtn');

    if (!modoEdicion) {
        inputs.forEach(input => {
            input.classList.remove('read-only');
            input.classList.add('editable');
        });
        btn.textContent = 'Cancelar';
        guardarBtn.classList.remove('hidden');
        modoEdicion = true;
    } else {
        inputs.forEach(input => {
            input.classList.remove('editable');
            input.classList.add('read-only');
        });
        btn.textContent = 'Editar';
        guardarBtn.classList.add('hidden');
        modoEdicion = false;
    }
}

function togglePassword(btn) {
    const text = document.getElementById('passwordText');
    if (text.style.display === 'none') {
        text.style.display = 'inline';
        btn.textContent = 'Ocultar';
    } else {
        text.style.display = 'none';
        btn.textContent = 'Mostrar';
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