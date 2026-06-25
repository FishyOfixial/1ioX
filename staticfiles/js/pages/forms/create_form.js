document.addEventListener('DOMContentLoaded', function () {
    const inputs = document.querySelectorAll('#form input, #form select');
    const dialCodesEl = document.getElementById('countryDialCodes');
    const dialCodes = dialCodesEl ? JSON.parse(dialCodesEl.textContent) : {};
    const countrySelect = document.querySelector('[data-country-select="true"]');
    const dialInput = document.querySelector('.dial-input');

    function syncDialCode() {
        if (!countrySelect || !dialInput) return;
        dialInput.value = dialCodes[countrySelect.value] || '';
    }

    syncDialCode();
    if (countrySelect) {
        countrySelect.addEventListener('change', syncDialCode);
    }

    inputs.forEach(input => {
        input.addEventListener('blur', function () {
            if (this.classList.contains('not-required')) return

            if (this.value.trim() === '') {
                this.classList.add('input-vacio');
            } else {
                this.classList.remove('input-vacio');
            }
        });

        input.addEventListener('input', function () {
            if (this.classList.contains('not-required')) return;

            if (this.value.trim() !== '') {
                this.classList.remove('input-vacio');
            }
        });
    });
});

document.getElementById('cancel').addEventListener('click', function () {
    window.location.href = '/usuarios'; // o donde quieras volver
});
