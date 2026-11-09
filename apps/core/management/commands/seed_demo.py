from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.catalog.models import Category, Framework, Product
from apps.downloads.models import ProductFile
from apps.pages.models import Page
from apps.services.models import Service


class Command(BaseCommand):
    help = "Create demo catalog data for local development. Safe to run more than once."

    def handle(self, *args, **options):
        fws = {}
        for name, slug in [("ISO 27001", "iso-27001"), ("SOC 2", "soc-2"), ("HIPAA", "hipaa"), ("NIST CSF", "nist-csf"), ("GDPR", "gdpr")]:
            fws[slug], _ = Framework.objects.get_or_create(slug=slug, defaults={"name": name})

        toolkits, _ = Category.objects.get_or_create(slug="toolkits", defaults={"name": "Toolkits", "order": 1})
        policies, _ = Category.objects.get_or_create(slug="policies", defaults={"name": "Policy templates", "order": 2})

        demo = [
            ("ISO 27001 Complete Toolkit", toolkits, ["iso-27001"], "149.00", True),
            ("SOC 2 Readiness Kit", toolkits, ["soc-2"], "129.00", True),
            ("Information Security Policy", policies, ["iso-27001", "soc-2", "nist-csf"], "29.00", True),
            ("HIPAA Risk Assessment Template", policies, ["hipaa"], "49.00", False),
        ]
        for title, cat, fw_slugs, price, featured in demo:
            slug = title.lower().replace(" ", "-")
            p, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": cat,
                    "price": Decimal(price),
                    "is_featured": featured,
                    "short_description": f"Audit-ready {title.lower()} you can customise in an afternoon.",
                    "whats_included": "Editable Word & Excel files\nImplementation guide\nFree updates for 12 months",
                },
            )
            p.frameworks.set([fws[s] for s in fw_slugs])
            if created:
                pf = ProductFile(product=p, title=f"{title} (ZIP)")
                pf.file.save("demo.txt", ContentFile(b"Demo deliverable\n"), save=True)

        Service.objects.get_or_create(
            slug="gap-assessment",
            defaults={"title": "ISO 27001 Gap Assessment", "summary": "Find out exactly what stands between you and certification.", "starting_price": Decimal("1500")},
        )
        for title, slug in [("About", "about"), ("Terms of Service", "terms"), ("Privacy Policy", "privacy"), ("Refund Policy", "refunds")]:
            Page.objects.get_or_create(slug=slug, defaults={"title": title, "body": f"<p>{title} content goes here.</p>", "show_in_footer": True})

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
