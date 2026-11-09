from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.core.models import SiteSettings
from apps.marketing import esp
from apps.marketing.models import Subscriber
from apps.orders.abandoned import send_reminders
from apps.orders.models import Order
from apps.orders.services import create_order_for_product, mark_order_paid


class NewsletterTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_unsubscribe_requires_post_and_token(self):
        self.client.post(reverse("marketing:subscribe"), {"email": "a@x.com"})
        sub = Subscriber.objects.get()
        self.assertIn(sub.get_unsubscribe_url(), mail.outbox[0].body)
        self.assertIn("List-Unsubscribe", mail.outbox[0].extra_headers)
        url = sub.get_unsubscribe_url()
        self.client.get(url)  # link scanners only GET
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)
        self.assertContains(self.client.post(url), "unsubscribed")
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.assertEqual(self.client.get(reverse("marketing:unsubscribe", args=["forged"])).status_code, 400)

    @override_settings(ESP_PROVIDER="mailerlite", ESP_API_KEY="k", ESP_LIST_ID="123")
    def test_mailerlite_sync_on_subscribe(self):
        with mock.patch("apps.marketing.esp.requests.post") as post, self.captureOnCommitCallbacks(execute=True):
            post.return_value.status_code = 200
            self.client.post(reverse("marketing:subscribe"), {"email": "m@x.com"})
        self.assertEqual(post.call_args.kwargs["json"], {"email": "m@x.com", "status": "active", "groups": ["123"]})
        self.assertIsNotNone(Subscriber.objects.get().esp_synced_at)

    @override_settings(ESP_PROVIDER="brevo", ESP_API_KEY="k", ESP_LIST_ID="7")
    def test_brevo_payload_and_error_recorded(self):
        sub = Subscriber.objects.create(email="b@x.com")
        with mock.patch("apps.marketing.esp.requests.post") as post:
            post.return_value.status_code = 400
            post.return_value.text = "bad"
            self.assertFalse(esp.sync(sub))
        self.assertEqual(post.call_args.kwargs["json"]["listIds"], [7])
        sub.refresh_from_db()
        self.assertIn("400", sub.esp_error)

    @override_settings(ESP_PROVIDER="mailchimp", ESP_API_KEY="abc-us21", ESP_LIST_ID="L1")
    def test_mailchimp_unsubscribe(self):
        sub = Subscriber.objects.create(email="c@x.com", is_active=False)
        with mock.patch("apps.marketing.esp.requests.put") as put:
            put.return_value.status_code = 200
            self.assertTrue(esp.sync(sub))
        self.assertIn("us21.api.mailchimp.com/3.0/lists/L1/members/", put.call_args.args[0])
        self.assertEqual(put.call_args.kwargs["json"]["status"], "unsubscribed")


class AbandonedCartTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="C", slug="c")
        self.product = Product.objects.create(title="Kit", slug="kit", category=cat, price=Decimal("10"),
                                              short_description="x", status="published")
        s = SiteSettings.load()
        s.abandoned_cart_emails = True
        s.save()

    def abandoned(self, email="a@x.com", hours=3):
        o = create_order_for_product(self.product)
        o.email = email
        o.status = Order.Status.CANCELLED
        o.save()
        Order.objects.filter(pk=o.pk).update(created_at=timezone.now() - timedelta(hours=hours))
        return o

    def test_reminder_sent_once_and_restores_cart(self):
        o = self.abandoned()
        self.assertEqual(send_reminders(), 1)
        self.assertEqual(send_reminders(), 0)
        link = next(line for line in mail.outbox[0].body.splitlines() if "/cart/restore/" in line).strip()
        resp = self.client.get(link.replace("http://localhost:8000", ""))
        self.assertRedirects(resp, reverse("orders:cart"))
        self.assertEqual(self.client.session["cart"]["items"], [{"product": self.product.pk, "tier": "single"}])
        o.refresh_from_db()
        self.assertIsNotNone(o.reminder_sent_at)

    def test_skips_buyers_too_recent_unsubscribed_and_disabled(self):
        self.abandoned("bought@x.com")
        paid = create_order_for_product(self.product)
        paid.email = "bought@x.com"
        paid.save()
        mark_order_paid(paid)
        self.abandoned("recent@x.com", hours=1)
        self.abandoned("optout@x.com")
        Subscriber.objects.create(email="optout@x.com", is_active=False)
        self.assertEqual(send_reminders(), 0)
        s = SiteSettings.load()
        s.abandoned_cart_emails = False
        s.save()
        self.abandoned("new@x.com")
        self.assertEqual(send_reminders(), 0)


class TrackingTests(TestCase):
    def test_no_tracking_until_configured_and_never_inline(self):
        html = self.client.get("/").content.decode()
        self.assertNotIn("tracking-config", html)
        self.assertNotIn("Cookie preferences", html)
        self.assertIn("js/vendor/htmx.min.js", html)
        self.assertNotIn("unpkg.com", html)
        s = SiteSettings.load()
        s.ga4_measurement_id = "G-ABC1234"
        s.search_console_verification = "tok_123"
        s.save()
        html = self.client.get("/").content.decode()
        self.assertIn('"ga4": "G-ABC1234"', html)
        self.assertIn('google-site-verification" content="tok_123"', html)
        self.assertIn("Cookie preferences", html)
        self.assertNotIn("googletagmanager.com/gtag", html)  # only loaded by JS after consent
