function goTo(element) {
    window.location.href = element.getAttribute('data-url');
}

let lastScrollY = window.scrollY;
const navbar = document.getElementById('navbar');

window.addEventListener('scroll', () => {
    const scrollDown = window.scrollY > lastScrollY;
    const scrolledMoreThanHalf = window.scrollY > (document.body.scrollHeight / 3);

    if (scrollDown && scrolledMoreThanHalf) {
        navbar.style.top = "-100px";
    } else {
        navbar.style.top = "0";
    }

    lastScrollY = window.scrollY;
});