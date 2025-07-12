document.addEventListener('DOMContentLoaded', function () {
    const inputs = document.querySelectorAll('#form input');

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