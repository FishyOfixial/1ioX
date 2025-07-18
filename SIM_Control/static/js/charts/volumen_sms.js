document.addEventListener('DOMContentLoaded', function () {
    const total = sms_suficiente + sms_bajo + sms_sin_volumen;

    const data = {
        labels: ['Suficiente', 'Bajo', 'Sin volumen'],
        datasets: [{
            label: 'Volumen de datos',
            data: [sms_suficiente, sms_bajo, sms_sin_volumen],
            backgroundColor: [`rgb(${primaryRGB})`, `rgb(${secondaryRGB})`, `rgb(${accentRGB})`],
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

    new Chart(document.getElementById('volumeSMSChart'), config);
});
