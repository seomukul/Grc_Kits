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
| Gumroad handles tax and file delivery | **We do.** Stripe Tax for VAT/GST/sales tax; our own secure download system. *Owner to confirm tax obligations with an accountant.* |
| "My Library" and Cart were Phase 2 / optional | Required at launch |
| Sales by source "Gumroad / Stripe" | Source = Stripe / coupon / affiliate + traffic source (UTM) |

---

## 2. Sitemap

| Page | Status |
|---|---|
| Home | 🟡 basic sections; needs slider, sections CMS (§3) |
| Products → Category → Product detail | 🟡 |
| Bundles | ⬜ |
| Services → service detail | 🟡 model + inquiry form; content from cyberprolab.com/services not migrated |
| Blog → Category → Post | 🟡 posts only, no blog categories |
| About Me | 🟡 generic CMS page; needs bio/certs/photo layout |
| Contact Us | ⬜ form with spam protection |
| My Library | 🟡 dashboard exists but needs password login; brief wants magic link |
| Cart / Checkout | 🟡 single-product "Buy now" only |
| Legal: Privacy, Terms, Refund, License Terms | 🟡 CMS pages exist (seeded), License Terms missing |
| Admin: Dashboard, Products, Orders, Customers, Coupons, Blog, Services, Settings | 🟡 Unfold CRUD only; no analytics, customers, coupons, settings |

## 3. Home page (sections toggleable + reorderable from admin)

⬜ Hero slider (3–5 slides: image, headline, sub-text, button) · ⬜ Trust bar · ✅ Featured products (manual) · ⬜ Top selling (auto, 30-day / all-time) · ⬜ New arrivals (auto) · 🟡 Browse by category/framework tiles · ⬜ Bundles / best value · ✅ Services preview · ⬜ Testimonials · ✅ Latest 3 blog posts · 🟡 Newsletter (no lead magnet yet) · ⬜ FAQ · 🟡 Footer (no social icons)

Frameworks to seed: ISO 27001, ISO 42001, NIST, BB CSF (Bangladesh Bank), PCI DSS, Network Security.

## 4. Products

### 4.1 Admin fields
- ✅ Title, slug, short + long description · ⬜ rich-text editor
- 🟡 Cover image · ⬜ gallery images · ⬜ preview video
- ✅ Price (USD) · ⬜ **license tiers: Single user / Team / Organization pricing** (owner idea #3)
- ✅ Category · ✅ framework tags (M2M) · 🟡 product type → change to *Excel tool, Word template, PDF, Bundle*
- 🟡 Multiple downloadable files (ZIP/XLSX/DOCX/PDF) · ⬜ **≥ 500 MB** uploads (needs object storage + direct upload)
- 🟡 Version number · ⬜ changelog, version history, "new version" email to past buyers
- ✅ What's included · ⬜ system requirements · ⬜ sample preview (PDF/screenshots)
- 🟡 Status: has active flag only → needs **Draft / Published / Hidden (unlisted) / Scheduled**
- ✅ Featured · ⬜ Bestseller (auto) · ⬜ New (auto)
- 🟡 SEO: meta title/description ✅, social share image ⬜
- ⬜ Duplicate / archive product

### 4.2 Storefront
- 🟡 Filters: category ✅, framework ✅, price range ⬜, rating ⬜ · ⬜ sorting (newest, popular, price)
- 🟡 Search (HTMX) · ⬜ suggestions/autocomplete
- 🟡 Detail page: price, buy, description, included, reviews ✅ · gallery, preview, FAQ, related products ⬜
- 🟡 Reviews: moderation ✅ · **verified buyers only** ⬜ (currently any logged-in user, flag only)
- ⬜ Bundles (discounted packs, framework "Complete Toolkit")
- 🟡 Coupons: Stripe promotion codes allowed at checkout · ⬜ own Coupon model (percent/fixed, expiry, usage limit, per-product or sitewide)
- ⬜ Wishlist (optional) · ⬜ Recently viewed

### 4.3 Purchase & delivery
- ✅ Guest checkout (name + email only)
- 🟡 Instant delivery: email link ✅ · download button on confirmation page ⬜
- 🟡 Secure downloads: files never public ✅ · download limit ✅ (default 10 → **brief: 5, admin-configurable**) · **signed links valid 24 h** ⬜ (currently the entitlement link lasts 365 days)
- ⬜ My Library via **magic link / one-time code** (no password)
- ⬜ Receipt / invoice PDF with order number (Stripe Checkout `invoice_creation` can do this)
- 🟡 Refund disables downloads ✅ (via `charge.refunded`) · admin "mark refunded" action ⬜ · disputes ⬜
- ⬜ Apple Pay / Google Pay / Link (enable in Stripe Dashboard; Checkout shows them automatically)
- ⬜ Stripe Tax

### 4.4 Marketing
- 🟡 Email list ✅ · welcome email ⬜ · export / Mailchimp-MailerLite-Brevo sync ⬜
- ⬜ Free lead magnet per category (sample template for email)
- ⬜ Abandoned cart email · ⬜ upsell/cross-sell "customers also bought"
- 🟡 Open Graph tags ✅ · share buttons ⬜
- ⬜ Affiliate program (later)

## 5. Admin analytics dashboard (most important admin feature)

All ⬜. Period selector: Today / Daily / Weekly / Monthly / Yearly / Custom.
Widgets: revenue + % change vs previous period · units & orders · AOV · **net revenue after Stripe fees & refunds** · revenue and units charts · top products (units, revenue) · sales by category/framework · **by country** · by source (coupon/affiliate) and traffic source · recent orders · refunds & disputes · new vs returning customers · funnel (visitors → views → checkout → purchase) · **CSV/Excel export for every table**.

Data we must capture on every order (from Stripe): amount, currency, **Stripe fee** (balance transaction), buyer email, **country**, coupon, UTM/referrer.

Management screens: Products (duplicate/archive/versions) · Orders (resend receipt / download link, refund) · **Customers** · Coupons & bundles · Reviews ✅ · Blog · Services · **Homepage** (slider, featured, section order) · **Settings** (site info, email templates, SEO defaults, legal text) · **Roles: Owner + Editor (blog only), 2FA**.

## 6. Blog

✅ Posts, SEO meta, sitemap, related products · ⬜ categories + sub-categories (create/rename/reorder) · ⬜ tags · ⬜ featured image ✅/author box ⬜ · ⬜ reading time · ⬜ rich-text editor (headings, tables, images, code, video, attachments) · 🟡 Draft/Published ✅, Scheduled ⬜ · ⬜ canonical + OG image per post · ⬜ TOC, related posts, share buttons · ⬜ category pages + search · 🟡 product CTA blocks (related products ✅) · ⬜ newsletter box per post · comments OFF · ⬜ RSS.

Starting categories: ISO 27001 · ISO 42001 / AI Governance · Risk Management · IT Audit · Bangladesh Bank / BB CSF · Network Security · Compliance Tips · Templates & Tools · News & Updates.

## 7. Services

- ⬜ Replicate every service from https://cyberprolab.com/services/ (owner's own site): same headings, descriptions, structure
- 🟡 Detail page: overview ✅ · deliverables, process steps, who it's for, FAQ ⬜
- 🟡 Enquiry form → emailed + saved as lead ✅ · service dropdown, optional file upload ⬜
- ⬜ Calendly / Cal.com embed (optional) · ✅ add/edit/reorder in admin

## 8. Other

- About Me (bio, certifications, experience, photo, LinkedIn) · Contact Us (form + spam protection, response-time note)
- Legal: Privacy, Terms, Refund, **License terms** (single-user vs team/org, no resale)
- Owner ideas: product previews · lifetime updates + "new version" email · testimonial wall · blog → product/service cross-promotion · i18n-ready (English first; Bangla/Arabic later) · GA4 + Search Console + conversion pixels · automated backups + uptime monitoring · anti-piracy (expiring links, limits, optional PDF watermark with buyer email) · "vote for the next toolkit" request page.

---

## 9. Proposed sprint plan

| Sprint | Scope |
|---|---|
| **1 — Catalog & delivery core** | Product status (draft/published/hidden/scheduled), product types, gallery/preview, license tiers, multiple files + versions/changelog, bundles. Downloads: 24 h signed links, limit 5 (admin setting). Object storage (Cloudflare R2/S3) for 500 MB files. Storefront filters + sorting. |
| **2 — Cart & Stripe launch-ready** | Cart (HTMX), coupons, multi-item Stripe Checkout, Stripe Tax, wallets, invoices/receipts, refunds + disputes, capture fees & country. Magic-link My Library. Confirmation page download buttons. Verified-buyer reviews. |
| **3 — Site content** | Homepage CMS (slider, trust bar, sections toggle/order, top selling, new arrivals, testimonials, FAQ). Services migrated from cyberprolab.com with full detail layout. About, Contact, License Terms. |
| **4 — Admin analytics** | Sales dashboard with period selector and charts, customers screen, CSV/Excel export, order actions (resend link/receipt), Site Settings, Editor role, 2FA. |
| **5 — Blog & marketing, launch** | Blog categories/tags/rich text/scheduling/TOC/RSS. Welcome email, ESP sync, lead magnets. GA4/Search Console, backups, uptime, production deploy. |

## 10. Open decisions for the owner

1. **License tiers** (Single / Team / Organization price per product): at launch or later? This changes the product, cart and order models, so it's cheaper to decide before Sprint 1.
2. **File storage:** Cloudflare R2 (recommended: cheap, no egress fees) or AWS S3? Needed for 500 MB files.
3. **Coupons:** our own coupon rules (per-product, usage limits, shown in our reports) vs Stripe promotion codes only (simpler, less control).
4. **Tax:** Stripe Tax on from day one? (Requires Stripe account details; confirm obligations with an accountant.)
5. **Services content:** migrate automatically from cyberprolab.com/services, or will you supply text/images?
