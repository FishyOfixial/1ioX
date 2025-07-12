document.addEventListener('DOMContentLoaded', function () {
    const total = activadas + desactivadas;

    const data = {
        labels: ['Activado', 'Desactivado'],
        datasets: [{
            label: 'Estado de SIMs',
            data: [activadas, desactivadas],
            backgroundColor: ['#002f60', '#e6f0ff'],
            hoverOffset: 20,
            borderRadius: 20,
            cutout: '70%',
        }]
    };

    const config = {
        type: 'doughnut',
        data: data,
        options: {
            rotation: -90,
            circumference: 180,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    title: {
                        text: `TOTAL: ${total}`,
                        display: true,
                        font: {
                            size: 24,
                            weight: 'bold',
                        }
                    },
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 18 }
                    }
                },
                tooltip: { enabled: true }
            }
        },
    };

    new Chart(document.getElementById('statusChart'), config);
});
