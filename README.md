# GRCkits.com

A digital storefront for GRC (governance, risk & compliance) templates and toolkits, plus consulting services and a blog.

**Stack:** Django 5.2 LTS · PostgreSQL · Tailwind CSS v4 (django-tailwind-cli, no Node) · HTMX 2 + Alpine.js 3 · Unfold admin · Stripe Checkout

---

## Quick start

Prerequisites: Python 3.12+, PostgreSQL 14+, and optionally the [Stripe CLI](https://docs.stripe.com/stripe-cli).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env            # then set SECRET_KEY, DATABASE_URL and Stripe test keys
createdb grckits

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo      # optional demo catalog, pages and a service

python manage.py tailwind runserver   # Django dev server + Tailwind watcher together
```

Open http://localhost:8000 (site) and http://localhost:8000/admin/ (Unfold admin).

The first `tailwind` command downloads the standalone Tailwind CLI binary into `.django_tailwind_cli/`. You don't need Node.

### Stripe locally

```bash
stripe login
stripe listen --forward-to localhost:8000/checkout/webhook/stripe/
```

Copy the `whsec_…` secret it prints into `STRIPE_WEBHOOK_SECRET` in `.env`, then restart the server. Pay with test card `4242 4242 4242 4242`, any future expiry date and any CVC.

### Tests

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps
```

---

## Project layout

```
config/
  settings/
    base.py        shared settings, all values from env
    dev.py         DEBUG, console email, debug-toolbar
    prod.py        HTTPS, HSTS, secure cookies, WhiteNoise manifest storage
    test.py        fast hasher, locmem email, dummy Stripe keys
  urls.py
apps/
  core/            custom User, TimeStampedModel, /health/, robots.txt, seed_demo command
  catalog/         Framework, Category, Product; list (HTMX search/filter) + detail
  payments/        Stripe Checkout session, success/cancel, webhook, StripeEvent log
  orders/          Order, OrderItem, fulfilment service, confirmation email
  downloads/       ProductFile (private storage), Entitlement (tokenised download links)
  reviews/         Review with moderation and verified-purchase flag (HTMX form)
  marketing/       newsletter Subscriber (HTMX form + honeypot)
  blog/            Post with SEO fields, related frameworks/products
  services/        consulting Service + ServiceInquiry lead form (HTMX)
  pages/           home page, CMS Page (about/terms/privacy), sitemaps
  dashboard/       customer account: downloads + order history
templates/         base.html, partials, and per-app templates
frontend/
  tailwind.css     Tailwind v4 source (theme tokens, plugins, utilities)
assets/            STATICFILES_DIRS: js/app.js; css/tailwind.css is generated (gitignored)
private_media/     paid files, never publicly served (gitignored)
```

## How purchase and delivery work

1. **Buy now** (`POST /checkout/<slug>/`) creates a `pending` Order and redirects to Stripe-hosted Checkout. The price comes from the database through `price_data`, so you don't have to create Stripe Price objects.
2. Stripe sends `checkout.session.completed` to `/checkout/webhook/stripe/`. The webhook:
   - verifies the signature;
   - stores the event in `StripeEvent` (its unique `event_id` makes retries harmless);
   - marks the order `paid` and creates one `Entitlement` per item;
   - after commit, emails the download links.
3. Buyers download through `/downloads/<token>/`. Files are streamed from `PRIVATE_MEDIA_ROOT` only while the order is paid, the link hasn't expired, and the download limit hasn't been reached.
4. The success page never fulfils anything. It only polls with HTMX until the webhook has marked the order paid.

The webhook also handles these events: `async_payment_succeeded`, `async_payment_failed`, `session.expired` and `charge.refunded`.

Guest checkout works. Logged-in buyers also see their purchases at `/dashboard/`.

## Frontend conventions

- **Tailwind v4** is configured in CSS (`frontend/tailwind.css`, `@theme`), not in a JS config. Brand colours are `brand-*` and `accent-*`. Shared utilities are `btn-primary`, `btn-secondary`, `card` and `container-page`.
- **HTMX:** views check `request.htmx` (django-htmx) and return a `_partial.html` for HTMX requests. `assets/js/app.js` adds the CSRF header to every HTMX request.
- **Alpine:** use it for small client-side state (mobile nav, toggles, button loading states). Put shared state in `Alpine.store("ui")`.
- HTMX and Alpine load from unpkg with pinned versions. Before launch, consider vendoring them into `assets/js/vendor/`, or add SRI hashes.

## Deployment notes

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py tailwind build
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

- Set every variable in `.env.example`. In production use `DEBUG=False`, live Stripe keys, a production webhook endpoint and SMTP credentials.
- WhiteNoise serves static files. Public uploads (`MEDIA_ROOT`) need a web server or object storage. `PRIVATE_MEDIA_ROOT` must be on persistent disk and must **not** be web-served. Moving it to private S3/R2 is planned for a later sprint.
- Health check: `GET /health/` returns `200` when the database is reachable, otherwise `503`.
- `python manage.py check --deploy` passes under `config.settings.prod`.

## Sprint 0: done

- [x] Django 5.2 project with split settings and env-driven config
- [x] PostgreSQL, custom `User` model from day one
- [x] 11 apps with models, admin, URLs, views and templates
- [x] Tailwind v4 + HTMX + Alpine base template (header, footer, messages, newsletter)
- [x] Unfold admin with grouped sidebar navigation
- [x] Stripe Checkout + idempotent webhook + private, tokenised downloads + email
- [x] Sitemap, robots.txt, canonical/OG tags, health check
- [x] Tests for the checkout → webhook → download flow

## Next sprints (suggested)

- Cart / multi-item checkout and bundles
- Signup and email verification (django-allauth), linking guest orders to accounts by email
- Private object storage (S3/R2) with signed URLs
- Rich text editor for blog and pages, image optimisation
- Newsletter provider sync (e.g. Mailchimp/Klaviyo), analytics, Stripe Tax
- CI pipeline (tests, ruff) and production hosting
