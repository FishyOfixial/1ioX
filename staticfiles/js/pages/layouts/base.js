const isMobile = window.innerWidth < 900;
const fontSize = isMobile ? 12 : 16
const titleSize = isMobile ? 16 : 22
const padding = isMobile ? 8 : 15
const rootStyles = getComputedStyle(document.documentElement);
const primaryRGB = rootStyles.getPropertyValue('--primary-color-rgb').trim();
const secondaryRGB = rootStyles.getPropertyValue('--secondary-color-rgb').trim();
const accentRGB = rootStyles.getPropertyValue('--accent-chart-rgb').trim();
const hoverRGB = rootStyles.getPropertyValue('--hover-color-rgb').trim();


function goTo(element, blank = false) {
    const url = element.getAttribute('data-url')
    if (url && blank)
        window.open(url, "_blank")
    else
        window.location.href = url
}

function toggleMenu() {
    const menuWrapper = document.querySelector('.menu-wrapper');
    menuWrapper.classList.toggle('show');
}

function toggleSessionMenu() {
    document.getElementById('sessionMenu').style.display =
        document.getElementById('sessionMenu').style.display === 'block' ? 'none' : 'block';
}

document.addEventListener('click', function (e) {
    const screenWidth = window.innerWidth;
    if (screenWidth <= 900) {
        document.getElementById('sessionMenu').style.display = 'flex';
        return
    }
    if (!e.target.closest('.nav-session')) {
        document.getElementById('sessionMenu').style.display = 'none';
        document.getElementById('langMenu').style.display = 'none';
    }
});

function toggleLanguageMenu(event) {
    event.stopPropagation();
    const langMenu = document.getElementById('langMenu');
    langMenu.style.display = langMenu.style.display === 'block' ? 'none' : 'block';
}

function setLanguage(lang) {
    window.location.href = `/set-lang/${lang}`;
}

function onResizeThreshold(threshold, callback) {
    let wasBelow = window.innerWidth < threshold;
    window.addEventListener('resize', () => {
        const isBelow = window.innerWidth < threshold;
        if (wasBelow !== isBelow) {
            callback(isBelow);
            wasBelow = isBelow;
        }
    });
}

onResizeThreshold(900, (isBelow) => {
    const key = 'resizeReloadDone';
    const lastState = sessionStorage.getItem(key);

    if (lastState !== String(isBelow)) {
        sessionStorage.setItem(key, String(isBelow));
        window.location.reload();
    }
});