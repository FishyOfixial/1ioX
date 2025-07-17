document.addEventListener('DOMContentLoaded', function () {

    const data = {
        labels: labels,
        datasets: [{
            label: 'SMS gastados',
            data: monthly_sms,
            backgroundColor: [
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${accentRGB}, 0.7)`
            ],
            borderColor: [
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${accentRGB}, 1)`
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

    new Chart(document.getElementById('monthlySmsUsageChart'), config);
});
