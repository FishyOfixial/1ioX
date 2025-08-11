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

const alerts = JSON.parse(document.getElementById('alerts').textContent);

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
        text.innerHTML =
            `<strong>${alerts.delete_hd}</strong> <br>${alerts.delete_lbl}`;
        action_input.value = "delete";

    } else if (action === "Active") {
        const idx = isActive === 'True' ? 0 : 1
        text.innerHTML =
            `<strong>${alerts.activate_hd[idx]}</strong><br>${alerts.activate_lbl[idx]}`
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