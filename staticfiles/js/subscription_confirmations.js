document.addEventListener("DOMContentLoaded", function () {
    var confirmationMessages = {
        extend: "¿Confirmas extender la suscripción? Se agregará tiempo adicional al vencimiento actual.",
        overwrite: "¿Confirmas cambiar el plan? El tiempo restante se perderá y será reemplazado por el nuevo plan.",
        suspend: "¿Confirmas suspender la suscripción? La SIM podría quedar sin servicio.",
        cancel: "¿Confirmas cancelar la suscripción? Esta acción es irreversible.",
        assign: "¿Asignar este plan a la SIM?"
    };

    var billingForms = document.querySelectorAll(".billing-card form");

    function setupCustomPlanFields() {
        var customPlanSelects = document.querySelectorAll(".billing-card .custom-plan-select");
        customPlanSelects.forEach(function (select) {
            var form = select.closest("form");
            if (!form) {
                return;
            }
            var wrap = form.querySelector(".custom-days-wrap");
            var input = form.querySelector(".custom-days-input");
            if (!wrap || !input) {
                return;
            }

            function toggleCustomInput() {
                var isCustom = select.value === "__custom__";
                wrap.classList.toggle("is-visible", isCustom);
                input.required = isCustom;
                if (!isCustom) {
                    input.value = "";
                }
            }

            select.addEventListener("change", toggleCustomInput);
            toggleCustomInput();
        });
    }

    function validateCustomDays(form) {
        var select = form.querySelector(".custom-plan-select");
        var input = form.querySelector(".custom-days-input");
        if (!select || !input) {
            return true;
        }
        if (select.value !== "__custom__") {
            return true;
        }
        var days = parseInt(input.value, 10);
        if (!Number.isInteger(days) || days < 1 || days > 365) {
            window.alert("Debes ingresar un valor de dias entre 1 y 365.");
            return false;
        }
        select.value = "";
        return true;
    }

    setupCustomPlanFields();

    billingForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!validateCustomDays(form)) {
                event.preventDefault();
                return;
            }

            var submitter = event.submitter || null;
            var action = (submitter && submitter.dataset.confirmAction) || form.dataset.action;
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
