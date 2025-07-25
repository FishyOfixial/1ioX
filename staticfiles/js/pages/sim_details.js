const data_volume = JSON.parse(document.getElementById('data-volume').textContent);
const data_used = JSON.parse(document.getElementById('data-used').textContent);
const sms_volume = JSON.parse(document.getElementById('sms-volume').textContent);
const sms_used = JSON.parse(document.getElementById('sms-used').textContent);
const monthly_use = JSON.parse(document.getElementById("monthly-use").textContent);
const label_form = document.getElementById('label-form');
const overlay = document.getElementById('overlay')
const inputs = label_form.querySelectorAll("input")

const labels = monthly_use.map(item => item.month);
const monthly_data = monthly_use.map(item => item.data_used);
const monthly_sms = monthly_use.map(item => item.sms_used);


function labelFormFunc() {
    if (label_form.style.display === "none") {
        label_form.style.display = "flex"
        overlay.style.display = "block"
    }
    else {
        label_form.style.display = "none"
        overlay.style.display = "none"

        inputs.forEach(input => {
            input.value = ""
        })
    }
}

const dragHandle = document.getElementById('drag')
let offsetX = 0, offsetY = 0, isDown = false;

dragHandle.addEventListener("mousedown", (e) => {
    isDown = true;
    offsetX = e.clientX - label_form.offsetLeft;
    offsetY = e.clientY = label_form.offsetTop;
});

document.addEventListener("mouseup", () => {
    isDown = false;
})

document.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    label_form.style.left = (e.clientX - offsetX) + "px";
    label_form.style.top = (e.clientY - offsetY) + "px";
})