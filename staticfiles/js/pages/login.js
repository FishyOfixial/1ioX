const input = document.getElementById("passwordField");
const icon = document.getElementById("toggleIcon");

function togglePasswordVisibility() {
    input.type = input.type === "text" ? "password" : "text";
    if (icon.alt === "ocultar") {
        icon.src = icon.dataset.view;
        icon.alt = "ver";
    } else {
        icon.src = icon.dataset.close;
        icon.alt = "ocultar";
    }
}

if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
    icon.addEventListener("touchend", (e) => {
        e.preventDefault();
        togglePasswordVisibility();
    });
} else {
    icon.addEventListener("click", togglePasswordVisibility);
}
