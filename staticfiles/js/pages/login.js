const input = document.getElementById("passwordField");
const icon = document.getElementById("toggleIcon");

icon.addEventListener("mousedown", () => {
    input.type = "text";
    icon.src = icon.dataset.close;
    icon.alt = "ocultar";
});

function hidePassword() {
    input.type = "password";
    icon.src = icon.dataset.view;
    icon.alt = "ver";
}

icon.addEventListener("mouseup", hidePassword);
icon.addEventListener("mouseleave", hidePassword);
