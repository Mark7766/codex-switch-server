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
