document.addEventListener('DOMContentLoaded', function () {

    const data = {
        labels: labels,
        datasets: [{
            label: 'Datos gastados',
            data: monthly_data,
            backgroundColor: [
                'rgba(0, 102, 255, 0.8)',
                'rgba(0, 102, 255, 0.8)',
                'rgba(0, 102, 255, 0.8)',
                'rgba(0, 102, 255, 0.8)',
                'rgba(0, 102, 255, 0.8)',
                'rgba(255, 62, 163, 0.8)'
            ],
            borderColor: [
                'rgba(0, 102, 255, 1)',
                'rgba(0, 102, 255, 1)',
                'rgba(0, 102, 255, 1)',
                'rgba(0, 102, 255, 1)',
                'rgba(0, 102, 255, 1)',
                'rgba(255, 62, 163, 1)'
            ],
            borderWidth: 1,
            borderRadius: 25
        }]
    };

    const config = {
        type: 'bar',
        data: data,
        options: {
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        },
    };

    new Chart(document.getElementById('monthlyDataUsageChart'), config);
});
