function refreshMonthlyUsage() {
    refreshFunc('/refresh-monthly-usage/')
}
function refreshSim() {
    refreshFunc('/refresh-sim/')
}
function refreshOrders() {
    refreshFunc('/refresh-orders/')
}
function refreshStatus() {
    document.getElementById("overlay").style.display = "flex";
    setTimeout(() => { window.location.reload(); }, 1000)
}
function refreshDataQuota() {
    refreshFunc('/refresh-data-quota/')
}
function refreshSMSQuota() {
    refreshFunc('/refresh-sms-quota/')
}

function refreshSMS(iccid) {
    refreshFunc(`/refresh-sms/${iccid}`)
}

function refreshFunc(link) {
    document.getElementById("overlay").style.display = "flex";

    fetch(`${link}`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken")
        }
    })
        .then(res => res.json())
        .then(data => {
            document.getElementById("overlay").style.display = "none";
            if (data.ok) {
                window.location.reload();
            } else {
                alert("Error: " + data.error);
            }
        })
        .catch(err => {
            document.getElementById("overlay").style.display = "none";
        });
}


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}