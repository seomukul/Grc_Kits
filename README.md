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
python manage.py seed_content   # starter content: 6 services, home slides, FAQs, legal drafts (safe in prod)
python manage.py seed_demo      # optional demo catalog for local dev (also runs seed_content)

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

## Cloudflare R2 (paid product files)

Paid files are stored in a **private** R2 bucket in production. Locally, if `R2_BUCKET_NAME` is empty, they go to `private_media/` instead.

1. Cloudflare dashboard → R2 → **Create bucket**, e.g. `grckits-files`. Don't connect a public domain to it.
2. R2 → **Manage API tokens** → create a token with *Object Read & Write* on that bucket only. Put the Account ID, Access Key ID and Secret in `.env` (`R2_*`).
3. Bucket → Settings → **CORS policy**. This lets the admin upload files straight from the browser:

   ```json
   [{"AllowedOrigins": ["https://grckits.com"], "AllowedMethods": ["PUT"], "AllowedHeaders": ["Content-Type"], "MaxAgeSeconds": 3600}]
   ```

With R2 enabled:
- **Admin uploads:** files (up to 5 GB) go directly to R2 through a presigned URL, so they never pass through Django or the VPS.
- **Buyer downloads:** buyers are redirected to a presigned URL that's valid for 5 minutes.

## Products, licenses and bundles

- **Status:** Draft, Published, Hidden (reachable only by direct link, never listed), or Scheduled (goes live at `publish_at`).
- **License tiers:** Single user always uses the product price. Add Team or Organization rows in the product's *Extra license tiers* inline. If you leave the price blank, it's calculated from the multiplier in **Admin → Site settings** (default ×2 and ×4).
- **Bundles:** set the product type to *Bundle* and pick the included products. A buyer gets one entitlement for each included product.
- **Files and versions:** every product has one or more *files*. Open a file to upload new *versions* with a changelog. Buyers always get the latest version. The "Email buyers about latest version" action sends each buyer a fresh link.
- **Site settings** (admin): download limit per file (default 5), link lifetime (default 24 h), tier multipliers, and the thresholds for the New and Bestseller badges.

## Cart, coupons and accounts

- **Cart:** the cart lives in the session, one line per product (choosing another license replaces the line). The checkout form collects the buyer's email and name and requires them to accept the License Terms.
- **Coupons** (Admin → Coupons): percent or fixed discount; sitewide or limited to chosen products; minimum order; start and end dates; limits on total uses and uses per customer. Only *paid* orders count as uses. Our code calculates the discount and stores each line's share. Stripe Checkout then shows it as a one-off Stripe coupon for exactly that amount. If a coupon brings the total to $0, the order is completed without Stripe.
- **Invoices:** when *Site settings → Stripe invoices* is on, Stripe creates a PDF invoice for every order (Stripe charges a small invoicing fee). The link appears in the email, in My Library and on the order page.
- **My Library:** customers sign in at `/account/login/` with a one-time email link that's valid for 20 minutes; there's no password. A buyer's first sign-in creates their account and links all their guest orders to it. Staff still use `/admin/` with a password.
- **Admin order actions:** *Refund in Stripe* (refunds and disables downloads) and *Resend receipt + download links*.
- **Reports data:** each order stores the Stripe fee, refunds, country and first-touch UTM/referrer. Sprint 4's dashboard uses these.
- **Wallets:** Apple Pay, Google Pay and Link need no code. Turn them on in Stripe Dashboard → Settings → Payment methods, and verify the domain for Apple Pay.

Stripe webhook events to enable: `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `charge.refunded`, `charge.dispute.created`, `charge.dispute.closed`.

## Site content (no code needed)

All of it lives under **Admin → Content**:
- **Home page sections:** 12 blocks (hero, trust bar, featured, top selling, new arrivals, browse, bundles, services, testimonials, blog, newsletter, FAQ). For each one you can turn it on or off, rename it, reorder it, or limit how many items it shows. Top selling has a choice of the last 30 days or all time. A section with nothing to show stays hidden.
- **Hero slides, Trust bar, Testimonials, FAQs:** you can mark a FAQ "show on products"; products can also have their own FAQs.
- **About page:** a single profile (photo, bio, certifications, experience timeline, stats).
- **Services:** overview, deliverables, process steps, who it's for, per-service FAQs and CTA text.
- **Leads (inquiries):** messages from service pages and the contact page, including attachments (private, staff-only download). Each lead is also emailed to *Site settings → Contact email*, with the customer as Reply-To.
- **Site settings:** contact email, response-time note, social links, Calendly or Cal.com link, and the newsletter lead-magnet file.

Spam protection on forms: a honeypot field, a minimum fill time, a signed form timestamp and a per-IP rate limit. There's no CAPTCHA.

## How purchase and delivery work

1. **Checkout** (`POST /checkout/` from the cart) re-checks the cart and coupon, creates a `pending` Order and redirects to Stripe-hosted Checkout. Prices come from the database through `price_data`, so you don't have to create Stripe Price objects.
2. Stripe sends `checkout.session.completed` to `/checkout/webhook/stripe/`. The webhook:
   - verifies the signature;
   - stores the event in `StripeEvent` (its unique `event_id` makes retries harmless);
   - marks the order `paid` and creates one `Entitlement` per item;
   - after commit, emails the download links.
3. Buyers download through **signed links** (`/downloads/<signed>/`) that expire after the *link lifetime* (24 h by default). A file can be downloaded until the per-file limit is reached, and every download is recorded in `DownloadLog`. A refunded order or a revoked entitlement blocks downloads immediately. Logged-in customers get fresh links from `/dashboard/`.
4. The success page never fulfils anything. It only polls with HTMX until the webhook has marked the order paid.



Guest checkout works. Buyers find past purchases in My Library (`/dashboard/`) after signing in with the email link.

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

## Sprint 1: done

- [x] Product status (draft/published/hidden/scheduled), types (Excel/Word/PDF/Bundle), gallery, preview video, sample file, system requirements, OG image
- [x] License tiers (Single/Team/Organization) with Site-settings multipliers
- [x] Bundles with savings display
- [x] Files with version history, changelog and "new version" buyer emails
- [x] Signed 24 h download links, per-file download limit, download log
- [x] Cloudflare R2 private storage with direct browser uploads
- [x] Shop filters (framework, type, price, rating), sorting, New/Bestseller/Sale badges, related products
- [x] Verified-buyer-only reviews, download buttons on the confirmation page

## Sprint 2: done

- [x] Session cart (HTMX), "customers also bought"
- [x] Own coupon system (percent/fixed, product scope, limits) applied in Stripe Checkout
- [x] Multi-item Stripe Checkout, license acceptance, Stripe invoices, free-order path
- [x] Webhook: Stripe fee, country, buyer name, invoice URL, partial/full refunds, disputes
- [x] Magic-link sign-in to My Library, guest orders linked by email
- [x] Admin: Refund in Stripe, Resend receipt, Coupons
- [x] First-touch UTM/referrer attribution on orders

## Sprint 3: done

- [x] Admin-managed home page: 12 toggleable/reorderable sections, hero slider, trust bar, testimonials, FAQ
- [x] 6 services migrated from cyberprolab.com and expanded (deliverables, process, audience, FAQs)
- [x] Lead form with service dropdown, private attachments, owner email, spam protection
- [x] About Me, Contact, License Terms and Refund Policy drafts
- [x] Site settings: contact, socials, booking link, lead magnet; welcome email
- [x] Product FAQs, footer social icons, header About/Contact links

## Next sprints (suggested)

- Cart / multi-item checkout and bundles
- Signup and email verification (django-allauth), linking guest orders to accounts by email
- Private object storage (S3/R2) with signed URLs
- Rich text editor for blog and pages, image optimisation
- Newsletter provider sync (e.g. Mailchimp/Klaviyo), analytics, Stripe Tax
- CI pipeline (tests, ruff) and production hosting
