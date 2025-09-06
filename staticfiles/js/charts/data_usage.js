document.addEventListener('DOMContentLoaded', function () {

    const data = {
        labels: month_label,
        datasets: [{
            label: data_usage_txt,
            data: data_usage,
            backgroundColor: [
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${primaryRGB}, 0.7)`,
                `rgba(${secondaryRGB}, 0.7)`
            ],
            borderColor: [
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${primaryRGB}, 1)`,
                `rgba(${secondaryRGB}, 1)`
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
                    console.log(filtered);
                    showCard({
                        id: 'topDataUsage',
                        label: label,
                        iccidOrArray: filtered,
                        emptyMsg: 'No hay SIMs que hayan consumido más del 75% del límite establecido.',
                        valueKey: 'data_volume_used',
                        formatValue: v => `${v.toFixed(2)} MB`
                    });
                }
            },
            maintainAspectRatio: true,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        },
    };

    new Chart(document.getElementById('dataUsageChart'), config);
});
