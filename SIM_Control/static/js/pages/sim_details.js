const data_volume = JSON.parse(document.getElementById('data-volume').textContent);
const data_used = JSON.parse(document.getElementById('data-used').textContent);
const sms_volume = JSON.parse(document.getElementById('sms-volume').textContent);
const sms_used = JSON.parse(document.getElementById('sms-used').textContent);
const monthly_use = JSON.parse(document.getElementById("monthly-use").textContent);

const labels = monthly_use.map(item => item.month);
const monthly_data = monthly_use.map(item => item.data_used);
const monthly_sms = monthly_use.map(item => item.sms_used);