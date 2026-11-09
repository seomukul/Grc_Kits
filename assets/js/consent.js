// Cookie consent + analytics loader. Nothing is loaded until the visitor clicks "Accept".
(function () {
  const cfgEl = document.getElementById("tracking-config");
  if (!cfgEl) return;
  const cfg = JSON.parse(cfgEl.textContent);
  const KEY = "grc_consent";
  const queue = [];

  // Public API used by pages: grcTrack("purchase", {...}). Queued until (and unless) consent is given.
  window.grcTrack = function (event, params) { queue.push([event, params || {}]); if (window.__grcLoaded) flush(); };

  function load(src, attrs) {
    const s = document.createElement("script");
    s.async = true; s.src = src;
    Object.assign(s, attrs || {});
    document.head.appendChild(s);
  }

  function start() {
    if (window.__grcLoaded) return;
    window.__grcLoaded = true;
    if (cfg.ga4) {
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { dataLayer.push(arguments); };
      gtag("js", new Date());
      gtag("config", cfg.ga4, { anonymize_ip: true });
      load("https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(cfg.ga4));
    }
    if (cfg.meta) {
      !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); }; if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = []; }(window, document);
      fbq("init", cfg.meta); fbq("track", "PageView");
      load("https://connect.facebook.net/en_US/fbevents.js");
    }
    if (cfg.linkedin) {
      window._linkedin_partner_id = cfg.linkedin;
      window._linkedin_data_partner_ids = [cfg.linkedin];
      window.lintrk = window.lintrk || function (a, b) { (window.lintrk.q = window.lintrk.q || []).push([a, b]); };
      load("https://snap.licdn.com/li/lms-analytics/insight.min.js");
    }
    flush();
  }

  function flush() {
    while (queue.length) {
      const [event, p] = queue.shift();
      if (window.gtag) gtag("event", event, p);
      if (window.fbq) {
        const map = { purchase: "Purchase", begin_checkout: "InitiateCheckout", add_to_cart: "AddToCart", view_item: "ViewContent", generate_lead: "Lead", sign_up: "CompleteRegistration" };
        if (map[event]) fbq("track", map[event], { value: p.value, currency: p.currency });
      }
    }
  }

  document.addEventListener("alpine:init", () => {
    Alpine.data("cookieConsent", () => ({
      open: false,
      init() {
        const choice = localStorage.getItem(KEY);
        if (choice === "granted") start();
        else if (!choice) this.open = true;
        window.addEventListener("open-cookie-settings", () => { this.open = true; });
      },
      accept() { localStorage.setItem(KEY, "granted"); this.open = false; start(); },
      reject() {
        localStorage.setItem(KEY, "denied"); this.open = false;
        if (window.__grcLoaded) location.reload();  // drop already-loaded trackers
      },
    }));
  });
})();
