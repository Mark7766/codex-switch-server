(function () {
  var nav = document.getElementById("nav");
  var toggle = document.getElementById("navToggle");
  var links = document.getElementById("navLinks");

  function onScroll() {
    if (window.scrollY > 10) {
      nav.classList.add("nav--glass");
      nav.classList.remove("nav--transparent");
    } else {
      nav.classList.add("nav--transparent");
      nav.classList.remove("nav--glass");
    }
  }

  if (nav && toggle && links) {
    nav.classList.add("nav--transparent");
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    toggle.addEventListener("click", function () {
      links.classList.toggle("nav__links--open");
    });
  }
})();

// ── Analytics: page view tracking ────────────────────────
(function () {
  var ANALYTICS_URL = '/api/v1/analytics/pageview';
  try {
    navigator.sendBeacon(ANALYTICS_URL, JSON.stringify({
      event_type: 'pageview',
      page: window.location.pathname
    }));
  } catch (e) { /* silently ignore */ }
})();

// ── Analytics: click tracking (elements with data-track) ──
document.addEventListener('click', function (e) {
  var el = e.target.closest('[data-track]');
  if (!el) return;
  try {
    navigator.sendBeacon('/api/v1/analytics/pageview', JSON.stringify({
      event_type: 'click',
      page: window.location.pathname,
      element_id: el.getAttribute('data-track')
    }));
  } catch (e) { /* silently ignore */ }
});

// ── Support: floating button + QA group modal ──────────────
(function () {
  var floatBtn = document.getElementById('supportFloat');
  var modal = document.getElementById('supportModal');
  if (!floatBtn || !modal) return;

  var overlay = modal.querySelector('.support-modal__overlay');
  var closeBtn = modal.querySelector('.support-modal__close');
  var card = modal.querySelector('.support-modal__card');

  function openModal() {
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    floatBtn.style.opacity = '0';
    if (card) card.focus();
  }

  function closeModal() {
    modal.classList.remove('is-open');
    document.body.style.overflow = '';
    floatBtn.style.opacity = '1';
    floatBtn.focus();
  }

  floatBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (overlay) overlay.addEventListener('click', closeModal);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.classList.contains('is-open')) {
      closeModal();
    }
  });

  // Breathe animation 3s after page load
  setTimeout(function () {
    floatBtn.classList.add('support-float--breathe');
  }, 3000);
})();
