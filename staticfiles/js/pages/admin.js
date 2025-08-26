const tableRows = document.querySelectorAll('#logTbody tr')

document.addEventListener('DOMContentLoaded', () => {
    const actionFilter = document.getElementById('actionFilter');
    const userFilter = document.getElementById('userFilter');
    const resetFilter = document.getElementById('resetFilter');

    function applyFilters() {
        const selectedAction = actionFilter.value;
        const selectedUser = userFilter.value;

        tableRows.forEach(row => {
            const action = row.cells[1].textContent.trim().toLowerCase();
            const id = row.getAttribute('data-id');

            const actionMatch = (selectedAction === 'all' || action === selectedAction.toLowerCase());
            const userMatch = (selectedUser === 'all' || id === selectedUser);

            row.style.display = (actionMatch && userMatch) ? '' : 'none';
        });
    }

    resetFilter.addEventListener('click', () => {
        tableRows.forEach(row => {
            actionFilter.value = 'all'
            userFilter.value = 'all'
            applyFilters()
        })
    })

    actionFilter.addEventListener('change', applyFilters);
    userFilter.addEventListener('change', applyFilters);
});