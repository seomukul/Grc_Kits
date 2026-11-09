import shutil
import tempfile
import time
from decimal import Decimal

from django.core import mail, signing
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.core.models import SiteSettings
from apps.marketing.models import Subscriber
from apps.pages.models import AboutProfile, FAQItem, HeroSlide, HomeSection
from apps.services.models import Service, ServiceInquiry

TMP = tempfile.mkdtemp()
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP}},
    "private": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP + "/private"}},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def old_ts():
    return signing.dumps(time.time() - 30, salt="form-ts")


@override_settings(STORAGES=STORAGES)
class ContentTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        cache.clear()
        call_command("seed_content", verbosity=0)
        cat = Category.objects.create(name="Kits", slug="kits")
        Product.objects.create(
            title="Featured Kit", slug="featured-kit", category=cat, price=Decimal("10"),
            short_description="x", status="published", is_featured=True,
        )

    def test_seed_content_is_idempotent(self):
        before = (Service.objects.count(), HeroSlide.objects.count(), FAQItem.objects.count())
        call_command("seed_content", verbosity=0)
        self.assertEqual(before, (Service.objects.count(), HeroSlide.objects.count(), FAQItem.objects.count()))
        self.assertEqual(Service.objects.count(), 6)
        self.assertEqual(HomeSection.objects.count(), 12)

    def test_home_renders_sections_in_order_and_respects_toggle(self):
        html = self.client.get("/").content.decode()
        self.assertIn("Audit-ready GRC templates", html)
        self.assertIn("Featured Kit", html)
        self.assertLess(html.index("Instant download"), html.index("Featured toolkits"))
        HomeSection.objects.filter(key="featured").update(is_enabled=False)
        self.assertNotIn("Featured toolkits", self.client.get("/").content.decode())
        HomeSection.objects.filter(key="faq").update(order=0)
        HomeSection.objects.filter(key="hero").update(order=99)
        html = self.client.get("/").content.decode()
        self.assertLess(html.index("Frequently asked questions"), html.index("Audit-ready GRC templates"))

    def test_empty_sections_are_hidden(self):
        # No testimonials or sales yet: those headings must not render.
        html = self.client.get("/").content.decode()
        self.assertNotIn("What customers say", html)
        self.assertNotIn("Top selling", html)

    def test_service_detail_shows_full_content(self):
        resp = self.client.get(reverse("services:detail", args=["vapt"]))
        self.assertContains(resp, "What you get")
        self.assertContains(resp, "How we work")
        self.assertContains(resp, "Who it's for")
        self.assertContains(resp, "Will testing disrupt")

    def test_inquiry_with_attachment_saved_and_emailed(self):
        s = SiteSettings.load()
        s.contact_email = "owner@example.com"
        s.save()
        resp = self.client.post(
            reverse("services:inquire", args=["vapt"]),
            {
                "name": "Ann", "email": "ann@example.com", "company": "Bank", "message": "Need a pentest",
                "ts": old_ts(), "attachment": SimpleUploadedFile("scope.pdf", b"%PDF-1.4 test"),
            },
        )
        self.assertContains(resp, "Your message is in")
        inquiry = ServiceInquiry.objects.get()
        self.assertEqual(inquiry.service.slug, "vapt")
        self.assertTrue(inquiry.attachment.name.startswith("inquiries/"))
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["ann@example.com"])

    def test_disallowed_attachment_type_rejected(self):
        resp = self.client.post(
            reverse("pages:contact"),
            {"name": "A", "email": "a@example.com", "message": "hi", "ts": old_ts(),
             "attachment": SimpleUploadedFile("evil.exe", b"MZ")},
        )
        self.assertContains(resp, "not allowed")
        self.assertFalse(ServiceInquiry.objects.exists())

    def test_contact_spam_protection(self):
        base = {"name": "Bot", "email": "b@example.com", "message": "spam"}
        self.client.post(reverse("pages:contact"), {**base, "ts": old_ts(), "website": "http://spam"})
        self.client.post(reverse("pages:contact"), {**base, "ts": signing.dumps(time.time(), salt="form-ts")})
        self.client.post(reverse("pages:contact"), {**base, "ts": "forged"})
        self.assertFalse(ServiceInquiry.objects.exists())
        resp = self.client.post(reverse("pages:contact"), {**base, "ts": old_ts(), "service": ""})
        self.assertContains(resp, "Your message is in")
        self.assertEqual(ServiceInquiry.objects.get().source, "contact")

    def test_contact_rate_limit(self):
        for i in range(7):
            self.client.post(reverse("pages:contact"), {"name": "A", "email": f"a{i}@x.com", "message": "m", "ts": old_ts()})
        self.assertEqual(ServiceInquiry.objects.count(), 5)

    def test_about_page(self):
        self.assertContains(self.client.get(reverse("pages:about")), "hasn't been set up")
        AboutProfile.objects.create(
            name="Sam", headline="GRC consultant", bio="<p>Hello</p>", certifications="CISA\nCISSP",
            stats="15+ | Years of experience",
        )
        resp = self.client.get(reverse("pages:about"))
        self.assertContains(resp, "CISSP")
        self.assertContains(resp, "Years of experience")

    def test_newsletter_lead_magnet_and_welcome_email(self):
        s = SiteSettings.load()
        s.lead_magnet_title = "Free Policy Sample"
        s.lead_magnet_file = SimpleUploadedFile("sample.pdf", b"%PDF")
        s.save()
        resp = self.client.post(reverse("marketing:subscribe"), {"email": "New@Example.com", "source": "home"})
        self.assertContains(resp, "Download Free Policy Sample")
        self.assertTrue(Subscriber.objects.filter(email="new@example.com").exists())
        self.assertIn("Free Policy Sample", mail.outbox[0].body)
        self.client.post(reverse("marketing:subscribe"), {"email": "new@example.com"})
        self.assertEqual(len(mail.outbox), 1)  # no second welcome

    def test_license_page_seeded(self):
        self.assertContains(self.client.get("/license/"), "Organization")

    def test_product_page_shows_faqs(self):
        resp = self.client.get(reverse("catalog:detail", args=["featured-kit"]))
        self.assertContains(resp, "How do I receive my files?")
