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
