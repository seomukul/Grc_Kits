# GRCkits.com — Requirements (Stripe-only edition)

Source: *GRC Digital Products Website – Requirements Brief for Developer* (owner's PDF, 6 pages).
The original brief launched on Gumroad and moved to Stripe in a second phase. **Decision (2026-11-09): launch directly on Stripe. There is no Gumroad phase.**

Status key: ✅ done in Sprint 0 · 🟡 partial · ⬜ not started

---

## 1. What changes because Gumroad is dropped

| Brief said (Gumroad phase) | Now (Stripe only) |
|---|---|
| Buy button opens the Gumroad overlay | Cart → Stripe-hosted Checkout from day one |
| Gumroad product URL field on every product | Removed |
| Gumroad API/Ping sales import, Phase 1 → 2 data migration | Removed. All sales come from Stripe webhooks |
| Payment-provider abstraction (Gumroad/Stripe switch) | Not needed. Payment logic stays isolated in `apps/payments` so another provider (e.g. Paddle/Lemon Squeezy for tax) could be added later |
| Gumroad handles tax and file delivery | **We do** file delivery with our own secure download system. Stripe Tax is not used (owner decision); tax obligations remain the owner's. |
| "My Library" and Cart were Phase 2 / optional | Required at launch |
| Sales by source "Gumroad / Stripe" | Source = Stripe / coupon / affiliate + traffic source (UTM) |

---

## 2. Sitemap

| Page | Status |
|---|---|
| Home | ✅ 12 admin-managed sections (§3) |
| Products → Category → Product detail | 🟡 |
| Bundles | ✅ (bundle products) |
| Services → service detail | ✅ 6 services migrated + expanded, full detail layout |
| Blog → Category → Post | ✅ categories + sub-categories, tags, search, RSS |
| About Me | ✅ layout + admin profile (owner fills bio, photo, certs) |
| Contact Us | ✅ lead form, spam protection, attachment, booking link |
| My Library | ✅ magic-link sign-in, files + orders + invoices |
| Cart / Checkout | ✅ session cart, coupons, multi-item Stripe Checkout |
| Legal: Privacy, Terms, Refund, License Terms | 🟡 License Terms + Refund drafted (need legal review); Privacy & Terms still placeholders |
| Admin: Dashboard, Products, Orders, Customers, Coupons, Blog, Services, Settings | ✅ sales dashboard, customers, coupons, site settings |

## 3. Home page (sections toggleable + reorderable from admin)

✅ Hero slider (auto-rotating, pauses on hover, reduced-motion aware) · ✅ Trust bar · ✅ Featured products (manual) · ✅ Top selling (auto, 30-day / all-time) · ✅ New arrivals (auto) · ✅ Browse by category/framework tiles · ✅ Bundles / best value · ✅ Services preview · ✅ Testimonials (admin-entered) · ✅ Latest 3 blog posts · ✅ Newsletter + lead magnet + welcome email · ✅ FAQ · ✅ Footer (social icons, contact email)

Every section can be switched on/off, retitled, reordered and limited in **Admin → Home page sections**. Empty sections hide themselves.

Frameworks to seed: ISO 27001, ISO 42001, NIST, BB CSF (Bangladesh Bank), PCI DSS, Network Security.

## 4. Products

### 4.1 Admin fields
- ✅ Title, slug, short + long description · ✅ rich-text editor (shared with the blog; long text collapses with "Read more")
- ✅ Cover image · ✅ gallery images · ✅ preview video
- ✅ Price (USD) · ✅ **license tiers: Single user / Team / Organization pricing** (owner idea #3)
- ✅ Category · ✅ framework tags (M2M) · ✅ product type: *Excel tool, Word template, PDF, Bundle*
- ✅ Multiple downloadable files (ZIP/XLSX/DOCX/PDF) · ✅ **≥ 500 MB** uploads (R2 direct upload)
- ✅ Version number · ✅ changelog, version history, "new version" email to past buyers
- ✅ What's included · ✅ system requirements · ✅ sample preview (PDF/screenshots)
- ✅ Status: **Draft / Published / Hidden (unlisted) / Scheduled**
- ✅ Featured · ✅ Bestseller (auto) · ✅ New (auto)
- ✅ SEO: meta title/description, social share image
- ✅ Duplicate product · ✅ archive (Draft/Hidden)

### 4.2 Storefront
- ✅ Filters: category, framework, type, price range, rating · ✅ sorting (newest, popular, price, rating)
- 🟡 Search (HTMX) · ⬜ suggestions/autocomplete
- ✅ Detail page: price, buy, description, included, reviews, gallery, preview, related products, FAQ (per product + shared)
- ✅ Reviews: moderation · **verified buyers only**
- ✅ Bundles (discounted packs, framework "Complete Toolkit")
- ✅ Coupons: own Coupon model (percent/fixed, expiry, total + per-customer limits, minimum order, per-product or sitewide)
- ⬜ Wishlist (optional) · ⬜ Recently viewed

### 4.3 Purchase & delivery
- ✅ Guest checkout (name + email only)
- ✅ Instant delivery: email link · download button on confirmation page
- ✅ Secure downloads: files never public · download limit 5 per file (Site settings) · **signed links valid 24 h** · download log
- ✅ My Library via **magic link** (no password); guest orders are linked to the account by email
- ✅ Receipt email + Stripe invoice PDF with order number (toggle in Site settings)
- ✅ Refunds (full disables downloads, partial tracked) · admin "Refund in Stripe" + "Resend receipt" actions · disputes (blocks downloads, restores if won, emails admin)
- 🟡 Apple Pay / Google Pay / Link: code ready (dynamic payment methods); owner turns them on in Stripe Dashboard → Payment methods
- ~~Stripe Tax~~ (owner decision: not used)

### 4.4 Marketing
- ✅ Email list · welcome email · unsubscribe link · CSV export · MailerLite / Brevo / Mailchimp sync
- 🟡 Free lead magnet (one sitewide file in Site settings; per-category later)
- ✅ Abandoned checkout reminder (opt-in setting, one email, restore-cart link) · ✅ "customers also bought" on cart page
- ✅ Open Graph tags · share buttons (blog)
- ⬜ Affiliate program (later)

## 5. Admin analytics dashboard (most important admin feature)

✅ Built in Sprint 4 (admin home page). Period selector: Today / Last 7 days / Last 30 days / This month / Last 12 months / This year / Custom range; charts bucket by day, week or month automatically.
Widgets: revenue + % change vs previous period · units & orders · AOV · **net revenue after Stripe fees & refunds** · revenue and units charts · top products (units, revenue) · sales by category/framework · **by country** · by source (coupon/affiliate) and traffic source · recent orders · refunds & disputes · new vs returning customers · funnel (visitors → views → checkout → purchase) · **CSV/Excel export for every table**.

Data captured on every order (Sprint 2 ✅): amount, discount, currency, **Stripe fee** (balance transaction), refunds, buyer email/name, **country**, coupon, first-touch UTM/referrer.

Widget status: ✅ revenue + % change · ✅ units & orders · ✅ AOV · ✅ net revenue (fees, refunds) · ✅ revenue / units charts · ✅ top products (units, revenue) · ✅ by discipline / framework / license tier / coupon · ✅ by country (table) · ✅ by traffic source (UTM/referrer) · ✅ recent orders · ✅ refunds & disputes · ✅ new vs returning · 🟡 funnel (checkout started → paid; visitor/product-view steps need GA4, Sprint 5) · ✅ CSV export (summary, orders, products, countries, sources, customers).

Management screens: ✅ Products (duplicate/archive/versions) · ✅ Orders (resend receipt / download link, refund, CSV) · ✅ **Customers** (guests included, purchase history, CSV) · ✅ Coupons & bundles · ✅ Reviews · 🟡 Blog (Sprint 5) · ✅ Services · ✅ **Homepage** · 🟡 **Settings** (site info, contact, social ✅; email templates / SEO defaults later) · ✅ **Roles: Owner + Editor (blog only), 2FA (authenticator app + backup codes)**.

## 6. Blog

✅ Categories + sub-categories (create/rename/reorder) · ✅ tags · ✅ featured image + author box · ✅ reading time · ✅ rich-text editor (headings, tables, images via media library, code blocks, embedded YouTube/Vimeo, downloadable attachments; HTML sanitized with nh3) · ✅ Draft / Scheduled / Published · ✅ SEO per post (meta, canonical, OG image, JSON-LD) + sitemap · ✅ TOC on long posts, related posts, share buttons · ✅ category / tag pages and search · ✅ product + service CTA blocks · ✅ newsletter box per post · comments OFF · ✅ RSS + Atom.

Starting categories (seeded): ISO 27001 · ISO 42001 / AI Governance · Risk Management · IT Audit · Bangladesh Bank / BB CSF · Network Security · Compliance Tips · Templates & Tools · News & Updates.

## 7. Services

- ✅ Replicate every service from https://cyberprolab.com/services/ (owner's own site): same headings, descriptions, structure
- ✅ Detail page: overview, deliverables, process steps, who it's for, FAQ
- ✅ Enquiry form → emailed (Reply-To customer) + saved as lead · service dropdown · optional file upload (private storage)
- ✅ Built-in Calendly-style booking on the contact page (visitor timezone, availability rules, days off, .ics invites, cancel link, admin confirm/cancel) · ✅ add/edit/reorder in admin

## 8. Other

- About Me (bio, certifications, experience, photo, LinkedIn) · Contact Us (form + spam protection, response-time note)
- Legal: Privacy, Terms, Refund, **License terms** (single-user vs team/org, no resale)
- Owner ideas (Sprint 5 ✅: GA4 + Search Console + Meta/LinkedIn pixels behind a cookie-consent banner, purchase/checkout events; automated backups + uptime monitoring documented in docs/DEPLOY.md): product previews · lifetime updates + "new version" email · testimonial wall · blog → product/service cross-promotion · i18n-ready (English first; Bangla/Arabic later) · GA4 + Search Console + conversion pixels · automated backups + uptime monitoring · anti-piracy (expiring links, limits, optional PDF watermark with buyer email) · "vote for the next toolkit" request page.

---

## 9. Proposed sprint plan

| Sprint | Scope |
|---|---|
| **1 — Catalog & delivery core** | Product status (draft/published/hidden/scheduled), product types, gallery/preview, license tiers, multiple files + versions/changelog, bundles. Downloads: 24 h signed links, limit 5 (admin setting). Cloudflare R2 private storage with direct uploads for 500 MB files. Storefront filters + sorting. |
| **2 — Cart & Stripe launch-ready** | Cart (HTMX), coupons, multi-item Stripe Checkout, wallets, invoices/receipts, refunds + disputes, capture fees & country. Magic-link My Library. Confirmation page download buttons. Verified-buyer reviews. |
| **3 — Site content** | Homepage CMS (slider, trust bar, sections toggle/order, top selling, new arrivals, testimonials, FAQ). Services migrated from cyberprolab.com with full detail layout. About, Contact, License Terms. |
| **4 — Admin analytics** | Sales dashboard with period selector and charts, customers screen, CSV/Excel export, order actions (resend link/receipt), Site Settings, Editor role, 2FA. |
| **5 — Blog & marketing, launch** | Blog categories/tags/rich text/scheduling/TOC/RSS. Welcome email, ESP sync, lead magnets. GA4/Search Console, backups, uptime, production deploy. |

## 10. Owner decisions (2026-11-09)

| # | Topic | Decision |
|---|---|---|
| 1 | **License tiers** | Build tier support in Sprint 1. Every product has a **Single user** license (the base price). **Team** and **Organization** are optional per product. Defaults: Team = up to 10 users in one organisation, about 2× the base price. Organization = unlimited users in one legal entity, about 4×. No resale or redistribution on any tier. Admin can override each tier's price per product. Cart, order and receipt store the chosen tier; the License Terms page explains the tiers. |
| 2 | **File storage** | **Cloudflare R2** for paid product files (private bucket). Downloads use presigned URLs valid for 24 h. Admin uploads go straight to R2, so 500 MB files never pass through Django. Implemented with `django-storages` (S3 API), so moving to VPS disk is just a settings change. Public images can live on R2 as well or on the VPS. |
| 3 | **Coupons** | **Own coupon system**: percent or fixed amount, expiry, total and per-customer usage limits, per-product or sitewide, minimum order. The discount is applied before creating the Stripe session; codes and discounts are stored on the order for reports. Stripe promotion codes will be turned off. |
| 4 | **Stripe Tax** | **Not used.** Prices are tax-inclusive USD. Tax obligations remain the owner's; revisit if needed. |
| 5 | **Services content** | Migrated from cyberprolab.com and expanded by us (see below). The owner reviews before launch. |

### Services to migrate (from cyberprolab.com/services and /training)

The source site has short descriptions only and no detail pages. For each service we write an expanded page: overview, deliverables, process steps, who it's for, FAQ, and a CTA. These are drafts for the owner to review.

1. **Information Security Management System (ISMS)**: ISO 27001 ISMS design and implementation
2. **VAPT**: vulnerability assessment, penetration testing, phishing simulation, remediation guidance
3. **IS Audit**: audit planning, risk-based auditing, controls assessment, compliance reporting
4. **GRC**: regulatory compliance, governance frameworks, ongoing risk management
5. **Risk Management**: risk identification, assessment and treatment, risk register, actionable insights
6. **Cyber Security Training**: workshops, simulations and awareness programs. Certification tracks: CISA, CISM, CISSP, CEH, CompTIA Security+, ISO/IEC 27001 Lead Implementer, ISO/IEC 27001 Lead Auditor. Delivery: in-person, virtual or hybrid.

Trust points to reuse: 10+ years of experience; CISSP-, CISA- and ISO 27001-certified experts; works with startups and enterprises.
