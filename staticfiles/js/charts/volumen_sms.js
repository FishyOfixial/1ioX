document.addEventListener('DOMContentLoaded', function () {
    const total = sms_suficiente + sms_bajo + sms_sin_volumen;

    const data = {
        labels: ['Suficiente', 'Bajo', 'Sin volumen'],
        datasets: [{
            label: 'Volumen de datos',
            data: [sms_suficiente, sms_bajo, sms_sin_volumen],
            backgroundColor: ['#002f60', '#0066ff', '#ff3ea3'],
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

    new Chart(document.getElementById('volumeSMSChart'), config);
});
