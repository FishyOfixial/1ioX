const isMobile = window.innerWidth < 900;
const fontSize = isMobile ? 12 : 18
const titleSize = isMobile ? 16 : 24
const padding = isMobile ? 8 : 15
const rootStyles = getComputedStyle(document.documentElement);
const primaryRGB = rootStyles.getPropertyValue('--primary-color-rgb').trim();
const secondaryRGB = rootStyles.getPropertyValue('--secondary-color-rgb').trim();
const accentRGB = rootStyles.getPropertyValue('--accent-chart-rgb').trim();
const hoverRGB = rootStyles.getPropertyValue('--hover-color-rgb').trim();


function goTo(element) {
    window.location.href = element.getAttribute('data-url');
}

function toggleMenu() {
    const menuWrapper = document.querySelector('.menu-wrapper');
    menuWrapper.classList.toggle('show');
}

document.addEventListener('DOMContentLoaded', () => {
    const images = document.querySelectorAll('.clickable-img');

    images.forEach(img => {
        img.addEventListener('click', () => {
            img.classList.remove('clicked');
            void img.offsetWidth;
            img.classList.add('clicked');
        });

        img.addEventListener('touchstart', () => {
            img.classList.remove('clicked');
            void img.offsetWidth;
            img.classList.add('clicked');
        });
    });
});
