const isMobile = () => window.innerWidth < 900;

function goTo(element, blank = false) {
    const url = element.getAttribute("data-url");
    if (!url) return;
    if (blank) {
        window.open(url, "_blank");
        return;
    }
    window.location.href = url;
}

function getMenuNodes() {
    return {
        menuWrapper: document.querySelector(".menu-wrapper"),
        hamburger: document.querySelector(".hamburger"),
        sessionTrigger: document.querySelector(".nav-session-trigger"),
        sessionMenu: document.getElementById("sessionMenu"),
        langMenu: document.getElementById("langMenu"),
    };
}

function closeMobileMenu() {
    const { menuWrapper, hamburger, sessionTrigger, sessionMenu, langMenu } = getMenuNodes();
    if (!menuWrapper || !hamburger) return;
    menuWrapper.classList.remove("show");
    hamburger.classList.remove("active");
    if (sessionMenu) sessionMenu.classList.remove("show");
    if (langMenu) langMenu.classList.remove("show");
    if (sessionTrigger) sessionTrigger.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-open");
}

function toggleMenu() {
    const { menuWrapper, hamburger, sessionMenu, langMenu } = getMenuNodes();
    if (!menuWrapper || !hamburger) return;
    const willShow = !menuWrapper.classList.contains("show");
    menuWrapper.classList.toggle("show", willShow);
    hamburger.classList.toggle("active", willShow);
    if (isMobile() && sessionMenu) {
        sessionMenu.classList.toggle("show", willShow);
    }
    if (!willShow && langMenu) {
        langMenu.classList.remove("show");
    }
    document.body.classList.toggle("menu-open", willShow && isMobile());
}

function toggleSessionMenu(event) {
    if (event) event.stopPropagation();
    if (isMobile()) return;
    const { sessionMenu, sessionTrigger, langMenu } = getMenuNodes();
    if (!sessionMenu) return;
    const willShow = !sessionMenu.classList.contains("show");
    sessionMenu.classList.toggle("show", willShow);
    if (sessionTrigger) sessionTrigger.setAttribute("aria-expanded", willShow ? "true" : "false");
    if (!willShow && langMenu) langMenu.classList.remove("show");
}

function toggleLanguageMenu(event) {
    event.stopPropagation();
    const { langMenu } = getMenuNodes();
    if (!langMenu) return;
    langMenu.classList.toggle("show");
}

function setLanguage(lang) {
    window.location.href = `/set-lang/${lang}`;
}

document.addEventListener("click", function (e) {
    const { menuWrapper, hamburger, sessionTrigger, sessionMenu, langMenu } = getMenuNodes();
    const insideNav = e.target.closest("nav");
    const insideSession = e.target.closest(".nav-session");

    if (isMobile()) {
        if (!insideNav && menuWrapper && menuWrapper.classList.contains("show")) {
            closeMobileMenu();
            return;
        }
        if (!insideSession) {
            if (langMenu) langMenu.classList.remove("show");
        }
        return;
    }

    if (!insideSession) {
        if (sessionMenu) sessionMenu.classList.remove("show");
        if (langMenu) langMenu.classList.remove("show");
        if (sessionTrigger) sessionTrigger.setAttribute("aria-expanded", "false");
    }
    if (menuWrapper) menuWrapper.classList.remove("show");
    if (hamburger) hamburger.classList.remove("active");
    document.body.classList.remove("menu-open");
});

window.addEventListener("resize", () => {
    if (!isMobile()) {
        const { menuWrapper, hamburger, sessionTrigger, sessionMenu, langMenu } = getMenuNodes();
        if (menuWrapper) menuWrapper.classList.remove("show");
        if (hamburger) hamburger.classList.remove("active");
        if (sessionMenu) sessionMenu.classList.remove("show");
        if (langMenu) langMenu.classList.remove("show");
        if (sessionTrigger) sessionTrigger.setAttribute("aria-expanded", "false");
        document.body.classList.remove("menu-open");
    }
});
