// Global JS for GRCkits. HTMX and Alpine are loaded in base.html.

// Send Django's CSRF token with every HTMX request.
document.addEventListener("htmx:configRequest", (event) => {
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (token) event.detail.headers["X-CSRFToken"] = token;
});

// Alpine store for small, page-wide UI state.
document.addEventListener("alpine:init", () => {
  Alpine.store("ui", { mobileNav: false });
});
