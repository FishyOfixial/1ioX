const passwordInput = document.getElementById("passwordField");
const usernameInput = document.getElementById("id_username");
const icon = document.getElementById("toggleIcon");
const rememberCredentials = document.getElementById("rememberCredentials");
const loginForm = document.querySelector(".login_form form");

const STORAGE_KEY_USERNAME = "trak_login_username";
const STORAGE_KEY_PASSWORD = "trak_login_password";

function clearRememberedCredentials() {
    localStorage.removeItem(STORAGE_KEY_USERNAME);
    localStorage.removeItem(STORAGE_KEY_PASSWORD);
}

function loadRememberedCredentials() {
    if (!usernameInput || !passwordInput || !rememberCredentials) {
        return;
    }

    const storedUsername = localStorage.getItem(STORAGE_KEY_USERNAME);
    const storedPassword = localStorage.getItem(STORAGE_KEY_PASSWORD);

    if (storedUsername !== null && storedPassword !== null) {
        usernameInput.value = storedUsername;
        passwordInput.value = storedPassword;
        rememberCredentials.checked = true;
    }
}

function togglePasswordVisibility() {
    if (!passwordInput || !icon) {
        return;
    }

    passwordInput.type = passwordInput.type === "text" ? "password" : "text";
    if (icon.alt === "ocultar") {
        icon.src = icon.dataset.view;
        icon.alt = "ver";
    } else {
        icon.src = icon.dataset.close;
        icon.alt = "ocultar";
    }
}

if (usernameInput) {
    usernameInput.setAttribute("autocomplete", "username");
}
if (passwordInput) {
    passwordInput.setAttribute("autocomplete", "current-password");
}

loadRememberedCredentials();

if (rememberCredentials) {
    rememberCredentials.addEventListener("change", () => {
        if (!rememberCredentials.checked) {
            clearRememberedCredentials();
        }
    });
}

if (loginForm) {
    loginForm.addEventListener("submit", () => {
        if (!usernameInput || !passwordInput || !rememberCredentials) {
            return;
        }

        if (rememberCredentials.checked) {
            localStorage.setItem(STORAGE_KEY_USERNAME, usernameInput.value);
            localStorage.setItem(STORAGE_KEY_PASSWORD, passwordInput.value);
        } else {
            clearRememberedCredentials();
        }
    });
}

if (icon) {
    if ("ontouchstart" in window || navigator.maxTouchPoints > 0) {
        icon.addEventListener("touchend", (e) => {
            e.preventDefault();
            togglePasswordVisibility();
        });
    } else {
        icon.addEventListener("click", togglePasswordVisibility);
    }
}
