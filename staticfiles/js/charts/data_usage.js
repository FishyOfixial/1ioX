document.addEventListener('DOMContentLoaded', function () {

    const data = {
        labels: month_label,
        datasets: [{
            label: 'Datos gastados',
            data: data_usage,
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
            onClick: (evt, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const label = data.labels[index];
                    const filtered = top_usage_data.filter(item => item.month === label);
                    showDataCard(label, filtered)
                }
            },
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        },
    };

    new Chart(document.getElementById('dataUsageChart'), config);
});
