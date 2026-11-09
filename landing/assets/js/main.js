const siteHeader = document.querySelector('.site-header');
const navToggle = document.querySelector('[data-nav-toggle]');
const navLinks = document.querySelectorAll('.site-nav a');
const revealElements = document.querySelectorAll('[data-reveal]');
const roomCarousels = document.querySelectorAll('[data-carousel]');
const checkinInput = document.querySelector('#checkin');
const checkoutInput = document.querySelector('#checkout');

function setNavOpen(isOpen) {
    if (!siteHeader || !navToggle) {
        return;
    }

    siteHeader.dataset.navOpen = String(isOpen);
    navToggle.setAttribute('aria-expanded', String(isOpen));
}

if (navToggle) {
    navToggle.addEventListener('click', () => {
        const isOpen = siteHeader?.dataset.navOpen === 'true';
        setNavOpen(!isOpen);
    });
}

navLinks.forEach((link) => {
    link.addEventListener('click', () => setNavOpen(false));
});

if (revealElements.length > 0) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) {
                return;
            }

            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
        });
    }, {
        threshold: 0.18,
        rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach((element) => {
        revealObserver.observe(element);
    });
}

roomCarousels.forEach((carousel) => {
    const track = carousel.querySelector('[data-room-track]');
    const slides = [...carousel.querySelectorAll('[data-room-slide]')];
    const dotsContainer = carousel.querySelector('.rooms-carousel__dots');
    const prevButton = carousel.querySelector('[data-room-prev]');
    const nextButton = carousel.querySelector('[data-room-next]');

    if (!track || slides.length === 0) {
        return;
    }

    let dots = [];

    if (dotsContainer) {
        const dotsLabel = dotsContainer.getAttribute('aria-label') ?? 'este carrusel';
        const carouselLabel = dotsLabel.replace(/^Selector de imágenes de /, '');

        dotsContainer.replaceChildren();

        slides.forEach((_, index) => {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'rooms-carousel__dot';
            dot.dataset.roomDot = String(index);
            dot.setAttribute('aria-label', `Mostrar imagen ${index + 1} de ${carouselLabel}`);
            dot.setAttribute('aria-pressed', String(index === 0));

            if (index === 0) {
                dot.classList.add('is-active');
            }

            dotsContainer.append(dot);
        });

        dots = [...dotsContainer.querySelectorAll('[data-room-dot]')];
    }

    let activeIndex = 0;
    let scrollTimer;

    function updateCarousel(index) {
        activeIndex = index;

        slides.forEach((slide, slideIndex) => {
            slide.setAttribute('aria-hidden', String(slideIndex !== activeIndex));
        });

        dots.forEach((dot, dotIndex) => {
            const isActive = dotIndex === activeIndex;
            dot.classList.toggle('is-active', isActive);
            dot.setAttribute('aria-pressed', String(isActive));
        });
    }

    function goToSlide(index) {
        const safeIndex = (index + slides.length) % slides.length;
        slides[safeIndex].scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'start'
        });
        updateCarousel(safeIndex);
    }

    prevButton?.addEventListener('click', () => {
        goToSlide(activeIndex - 1);
    });

    nextButton?.addEventListener('click', () => {
        goToSlide(activeIndex + 1);
    });

    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            goToSlide(index);
        });
    });

    track.addEventListener('scroll', () => {
        window.clearTimeout(scrollTimer);
        scrollTimer = window.setTimeout(() => {
            const nextIndex = Math.round(track.scrollLeft / track.clientWidth);
            updateCarousel(Math.max(0, Math.min(slides.length - 1, nextIndex)));
        }, 60);
    });

    updateCarousel(0);
});

function isoDateFromOffset(offsetDays = 0) {
    const date = new Date();
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() + offsetDays);
    return formatDate(date);
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function syncDateConstraints() {
    if (!checkinInput || !checkoutInput) {
        return;
    }

    const today = isoDateFromOffset(0);
    checkinInput.min = today;
    if (checkinInput.value) {
        const nextDay = new Date(`${checkinInput.value}T00:00:00`);
        nextDay.setDate(nextDay.getDate() + 1);
        checkoutInput.min = formatDate(nextDay);
    } else {
        checkoutInput.min = isoDateFromOffset(1);
    }

    if (checkinInput.value && checkoutInput.value && checkoutInput.value <= checkinInput.value) {
        checkoutInput.value = '';
    }
}

function validateStayDates() {
    if (!checkinInput || !checkoutInput) {
        return true;
    }

    checkoutInput.setCustomValidity('');

    if (!checkinInput.value || !checkoutInput.value) {
        return true;
    }

    if (checkoutInput.value <= checkinInput.value) {
        checkoutInput.setCustomValidity('La fecha de salida debe ser posterior al check-in.');
        return false;
    }

    return true;
}

syncDateConstraints();

checkinInput?.addEventListener('change', () => {
    syncDateConstraints();
    validateStayDates();
});

checkoutInput?.addEventListener('change', validateStayDates);
