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
