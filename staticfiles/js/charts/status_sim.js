document.addEventListener('DOMContentLoaded', function () {
    const total = activadas + desactivadas;

    const data = {
        labels: ['Activado', 'Desactivado'],
        datasets: [{
            label: 'Estado de SIMs',
            data: [activadas, desactivadas],
            backgroundColor: [`rgb(${primaryRGB})`, `rgb(${secondaryRGB})`],
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
                            size: titleSize,
                            weight: 'bold',
                        }
                    },
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: padding,
                        font: { size: fontSize }
                    }
                },
                tooltip: { enabled: true }
            }
        },
    };

    new Chart(document.getElementById('statusChart'), config);
});
