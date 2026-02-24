document.addEventListener("DOMContentLoaded", function () {
    var confirmationMessages = {
        extend: "\u00bfConfirmas extender la suscripci\u00f3n? Se agregar\u00e1 tiempo adicional al vencimiento actual.",
        overwrite: "\u00bfConfirmas cambiar el plan? El tiempo restante se perder\u00e1 y ser\u00e1 reemplazado por el nuevo plan.",
        suspend: "\u00bfConfirmas suspender la suscripci\u00f3n? La SIM podr\u00eda quedar sin servicio.",
        cancel: "\u00bfConfirmas cancelar la suscripci\u00f3n? Esta acci\u00f3n es irreversible.",
        assign: "\u00bfAsignar este plan a la SIM?"
    };

    var billingForms = document.querySelectorAll(".billing-card form");

    billingForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var action = form.dataset.action;
            var message = confirmationMessages[action];

            if (!message) {
                return;
            }

            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
});