let modoEdicion = false;

function toggleEdicion(btn) {
    const inputs = document.querySelectorAll('#editForm input');
    const editBtn = document.getElementById('toggleEditBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const guardarBtn = document.getElementById('guardarBtn');
    const generateBtn = document.getElementById('generatePasswordBtn');
    const passwordInput = document.getElementById('newPasswordField');
    const confirmInput = document.getElementById('confirmPasswordField');
    const icon = document.getElementById("toggleIcon");
    const passwordPreview = document.getElementById('generatedPasswordPreview');

    if (!modoEdicion) {
        inputs.forEach(input => {
            input.classList.remove('read-only');
            input.readOnly = false;
        });
        if (generateBtn) {
            generateBtn.classList.remove('hidden');
        }
        if (icon) {
            icon.classList.remove('hidden');
        }
        editBtn.style.display = 'none';
        cancelBtn.style.display = 'block';
        guardarBtn.classList.remove('hidden');
        modoEdicion = true;
    } else {
        inputs.forEach(input => {
            input.readOnly = true
            input.classList.add('read-only');
        });
        if (passwordInput) {
            passwordInput.value = '';
            passwordInput.type = 'password';
        }
        if (confirmInput) {
            confirmInput.value = '';
            confirmInput.type = 'password';
        }
        if (passwordPreview) {
            passwordPreview.textContent = '';
            passwordPreview.classList.add('hidden');
        }
        if (icon) {
            icon.src = icon.dataset.view;
            icon.alt = "ver";
            icon.classList.add('hidden');
        }
        if (generateBtn) {
            generateBtn.classList.add('hidden');
        }
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
    const passwordInput = document.getElementById('newPasswordField');
    const confirmInput = document.getElementById('confirmPasswordField');
    const generateBtn = document.getElementById('generatePasswordBtn');
    const passwordPreview = document.getElementById('generatedPasswordPreview');

    const setEyeState = (isVisible) => {
        if (!icon) return;
        icon.src = isVisible ? icon.dataset.close : icon.dataset.view;
        icon.alt = isVisible ? "ocultar" : "ver";
    };

    if (icon && passwordInput) {
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
            icon.addEventListener("touchend", (e) => {
                e.preventDefault();
                togglePasswordVisibility();
            });
        } else {
            icon.addEventListener("click", togglePasswordVisibility);
        }
    }

    function togglePasswordVisibility() {
        if (!passwordInput) return;
        const isHidden = passwordInput.type === 'password';
        passwordInput.type = isHidden ? 'text' : 'password';
        setEyeState(isHidden);
    }

    if (generateBtn && passwordInput && confirmInput) {
        generateBtn.addEventListener('click', () => {
            const temporaryPassword = generateTemporaryPassword();
            passwordInput.value = temporaryPassword;
            confirmInput.value = temporaryPassword;
            passwordInput.type = 'text';
            setEyeState(true);
            updatePasswordPreview();
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', updatePasswordPreview);
    }

    const form = document.getElementById('editForm');
    if (form && passwordInput && confirmInput) {
        form.addEventListener('submit', async (e) => {
            const hasPasswordChange = Boolean(passwordInput.value || confirmInput.value);
            e.preventDefault();
            if (hasPasswordChange && passwordInput.value !== confirmInput.value) {
                alert('La confirmación de contraseña no coincide.');
                return;
            }

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const payload = await response.json();
                if (!response.ok || !payload.ok) {
                    alert(payload.error || 'No se pudo guardar el usuario.');
                    return;
                }

                if (hasPasswordChange) {
                    const copied = await copyToClipboard(passwordInput.value);
                    if (copied) {
                        alert('Contraseña guardada y copiada al portapapeles.');
                    } else {
                        alert('Contraseña guardada. No se pudo copiar automáticamente al portapapeles.');
                    }
                } else {
                    alert(payload.message || 'Usuario actualizado correctamente.');
                }

                if (passwordInput) {
                    passwordInput.value = '';
                    passwordInput.type = 'password';
                }
                if (confirmInput) {
                    confirmInput.value = '';
                    confirmInput.type = 'password';
                }

                if (modoEdicion) {
                    toggleEdicion();
                }
            } catch (err) {
                alert('Error de red al guardar. Inténtalo de nuevo.');
            }
        });
    }

    function generateTemporaryPassword() {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
        let value = '';
        for (let i = 0; i < 12; i += 1) {
            value += chars[Math.floor(Math.random() * chars.length)];
        }
        return value;
    }

    async function copyToClipboard(value) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(value);
                return true;
            }
        } catch (err) {
            // Fallback below.
        }

        try {
            const textarea = document.createElement('textarea');
            textarea.value = value;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(textarea);
            return ok;
        } catch (err) {
            return false;
        }
    }

    function updatePasswordPreview() {
        if (!passwordPreview || !passwordInput) return;
        if (!passwordInput.value) {
            passwordPreview.textContent = '';
            passwordPreview.classList.add('hidden');
            return;
        }
        passwordPreview.textContent = `Temporal: ${passwordInput.value}`;
        passwordPreview.classList.remove('hidden');
    }
});
