document.addEventListener('DOMContentLoaded', function () {

    const data = {
        labels: month_label,
        datasets: [{
            label: sms_usage_txt,
            data: data_sms,
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
                    const filtered = top_sms_data.filter(item => item.month === label);
                    showCard({
                        id: 'topSMSUsage',
                        label: label,
                        iccidOrArray: filtered,
                        emptyMsg: 'No hay SIMs que hayan consumido más de 20 SMS.',
                        valueKey: 'sms_used'
                    });
                }
            },
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } },
        },
    };

    new Chart(document.getElementById('smsUsageChart'), config);
});
