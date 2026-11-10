from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.catalog.models import Category, Framework, LicenseTier, Product, ProductLicense
from apps.core.models import SiteSettings
from apps.downloads.models import ProductFile, ProductFileVersion
from apps.pages.models import Page

FRAMEWORKS = [
    ("ISO 27001", "iso-27001"),
    ("ISO 42001", "iso-42001"),
    ("NIST CSF", "nist-csf"),
    ("BB CSF", "bb-csf"),
    ("PCI DSS", "pci-dss"),
    ("SOC 2", "soc-2"),
    ("Network Security", "network-security"),
]

# (name, slug, icon, description): "disciplines" shown as tiles on the home page.
CATEGORIES = [
    ("Information Security & Cybersecurity", "toolkits", "shield", "ISO 27001, NIST CSF, SOC 2 and the controls that protect your information."),
    ("Data Privacy & Protection", "policies", "lock", "GDPR-style privacy programs, notices, DPIAs and records of processing."),
    ("Governance, Risk & Compliance", "risk-audit", "scale", "Risk registers, compliance trackers and board-ready reporting."),
    ("Audit & Assurance", "checklists", "audit", "Internal audit programs, checklists and evidence trackers."),
    ("AI Governance", "ai-governance", "badge", "ISO 42001 and responsible-AI policies for teams adopting AI."),
    ("Banking & Financial Regulation", "banking", "globe", "Bangladesh Bank BB CSF, PCI DSS and financial-sector requirements."),
]

# title, category slug, type, frameworks, price, featured, team/org tiers
PRODUCTS = [
    ("ISO 27001 Risk Register", "risk-audit", "excel", ["iso-27001"], "49.00", True, True),
    ("Information Security Policy Pack", "toolkits", "word", ["iso-27001", "nist-csf", "soc-2"], "79.00", True, True),
    ("ISO 42001 AI Governance Policy", "ai-governance", "word", ["iso-42001"], "59.00", False, True),
    ("PCI DSS Readiness Checklist", "banking", "pdf", ["pci-dss"], "29.00", False, False),
    ("BB CSF Compliance Tracker", "banking", "excel", ["bb-csf"], "69.00", True, True),
    ("Firewall Rule Review Checklist", "checklists", "pdf", ["network-security"], "19.00", False, False),
]


class Command(BaseCommand):
    help = "Create demo catalog data for local development. Safe to run more than once."

    def handle(self, *args, **options):
        SiteSettings.load()
        fws = {}
        for i, (name, slug) in enumerate(FRAMEWORKS):
            fws[slug], _ = Framework.objects.get_or_create(slug=slug, defaults={"name": name, "order": i})
        cats = {}
        for i, (name, slug, icon, desc) in enumerate(CATEGORIES):
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "order": i, "icon": icon, "description": desc}
            )

        products = {}
        for title, cat, ptype, fw_slugs, price, featured, tiers in PRODUCTS:
            p = self._product(title, cats[cat], ptype, price, featured)
            p.frameworks.set([fws[s] for s in fw_slugs])
            if tiers:
                for tier in (LicenseTier.TEAM, LicenseTier.ORGANIZATION):
                    ProductLicense.objects.get_or_create(product=p, tier=tier)
            self._files(p, ["Main file", "Implementation guide"] if ptype != "pdf" else ["Checklist"])
            products[title] = p

        bb = products.get("BB CSF Compliance Tracker")
        if bb and not bb.description:
            from ._demo_descriptions import BB_CSF

            bb.description = BB_CSF.strip()
            bb.save(update_fields=["description"])

        bundle = self._product("ISO 27001 Complete Toolkit", cats["toolkits"], "bundle", "99.00", True)
        bundle.frameworks.set([fws["iso-27001"]])
        bundle.bundle_items.set(
            [products["ISO 27001 Risk Register"], products["Information Security Policy Pack"]]
        )
        for tier in (LicenseTier.TEAM, LicenseTier.ORGANIZATION):
            ProductLicense.objects.get_or_create(product=bundle, tier=tier)

        for title, slug in [
            ("About", "about"),
            ("Terms of Service", "terms"),
            ("Privacy Policy", "privacy"),
            ("Refund Policy", "refunds"),
            ("License Terms", "license"),
        ]:
            Page.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "body": f"<p>{title} content goes here.</p>", "show_in_footer": True},
            )
        call_command("seed_content")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))

    def _product(self, title, category, ptype, price, featured):
        slug = title.lower().replace(" ", "-")
        p, _ = Product.objects.get_or_create(
            slug=slug,
            defaults={
                "title": title,
                "category": category,
                "product_type": ptype,
                "price": Decimal(price),
                "is_featured": featured,
                "status": Product.Status.PUBLISHED,
                "short_description": f"Audit-ready {title} you can customise in an afternoon.",
                "whats_included": "Editable files\nImplementation guide\nFree lifetime updates",
                "system_requirements": "Microsoft Excel 2016+" if ptype == "excel" else "",
            },
        )
        return p

    def _files(self, product, titles):
        for i, t in enumerate(titles):
            pf, created = ProductFile.objects.get_or_create(product=product, title=t, defaults={"order": i})
            if created:
                v = ProductFileVersion(product_file=pf, version="1.0", changelog="Initial release.")
                v.file.save(f"{product.slug}-{i + 1}.txt", ContentFile(b"Demo deliverable\n"), save=True)
