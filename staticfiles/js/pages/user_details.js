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
