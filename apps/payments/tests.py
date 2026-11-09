import json
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, LicenseTier, Product, ProductLicense
from apps.core.models import SiteSettings
from apps.downloads.models import DownloadLog, Entitlement, ProductFile, ProductFileVersion
from apps.downloads.notifications import notify_buyers_of_update
from apps.orders.models import Order
from apps.orders.services import create_order_for_product, mark_order_paid
from apps.payments.models import StripeEvent

TMP = tempfile.mkdtemp()
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP}},
    "private": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP}},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_product(title, category, price="100.00", **kw):
    kw.setdefault("status", Product.Status.PUBLISHED)
    return Product.objects.create(
        title=title, slug=title.lower().replace(" ", "-"), category=category,
        price=Decimal(price), short_description="x", **kw,
    )


def add_file(product, title="Kit", content=b"zipdata", version="1.0"):
    pf = ProductFile.objects.create(product=product, title=title)
    v = ProductFileVersion(product_file=pf, version=version)
    v.file.save(f"{title}.zip", ContentFile(content), save=True)
    return pf


@override_settings(STORAGES=STORAGES, USE_R2=False)
class BaseTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.cat = Category.objects.create(name="Toolkits", slug="toolkits")
        self.product = make_product("ISO Kit", self.cat, "149.00")
        self.file = add_file(self.product)

    def paid_order(self, product=None, tier=LicenseTier.SINGLE, user=None):
        order = create_order_for_product(product or self.product, user=user, license_tier=tier)
        order.email = "buyer@example.com"
        order.save()
        return mark_order_paid(order)


class CheckoutWebhookTests(BaseTestCase):
    def _event(self, order, event_id="evt_1", etype="checkout.session.completed", payment_status="paid"):
        return {
            "id": event_id,
            "type": etype,
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "payment_status": payment_status,
                    "client_reference_id": str(order.number),
                    "metadata": {"order_number": str(order.number)},
                    "customer_details": {"email": "buyer@example.com"},
                    "payment_intent": "pi_123",
                }
            },
        }

    def _post_webhook(self, event):
        fake = mock.MagicMock()
        fake.__getitem__.side_effect = event.__getitem__
        fake.to_dict.return_value = event
        with mock.patch("stripe.Webhook.construct_event", return_value=fake):
            return self.client.post(
                reverse("payments:stripe_webhook"), data=json.dumps(event),
                content_type="application/json", HTTP_STRIPE_SIGNATURE="t=1,v1=x",
            )

    def _checkout(self, **post):
        session = mock.MagicMock(id="cs_test_1", url="https://checkout.stripe.com/c/pay/cs_test_1")
        with mock.patch("apps.payments.views.get_client") as gc:
            gc.return_value.v1.checkout.sessions.create.return_value = session
            resp = self.client.post(reverse("payments:create", args=[self.product.slug]), post)
        return resp, gc

    def test_checkout_redirects_to_stripe_with_single_price(self):
        resp, gc = self._checkout()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://checkout.stripe.com/c/pay/cs_test_1")
        params = gc.return_value.v1.checkout.sessions.create.call_args.kwargs["params"]
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 14900)
        self.assertNotIn("allow_promotion_codes", params)

    def test_checkout_team_license_uses_multiplier(self):
        ProductLicense.objects.create(product=self.product, tier=LicenseTier.TEAM)
        resp, gc = self._checkout(license="team")
        params = gc.return_value.v1.checkout.sessions.create.call_args.kwargs["params"]
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 29800)  # 149 × 2
        self.assertIn("Team license", params["line_items"][0]["price_data"]["product_data"]["name"])
        self.assertEqual(Order.objects.get().items.get().license_tier, "team")

    def test_checkout_rejects_tier_not_offered(self):
        resp, gc = self._checkout(license="organization")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.product.get_absolute_url())
        gc.return_value.v1.checkout.sessions.create.assert_not_called()

    def test_draft_product_cannot_be_bought(self):
        self.product.status = Product.Status.DRAFT
        self.product.save()
        resp, _ = self._checkout()
        self.assertEqual(resp.status_code, 404)

    def test_webhook_marks_paid_grants_download_and_emails(self):
        order = create_order_for_product(self.product)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_webhook(self._event(order))
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        ent = Entitlement.objects.get(order_item__order=order)
        self.assertEqual(ent.max_downloads, 5)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/downloads/", mail.outbox[0].body)

    def test_webhook_is_idempotent(self):
        order = create_order_for_product(self.product)
        self._post_webhook(self._event(order))
        resp = self._post_webhook(self._event(order))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(StripeEvent.objects.count(), 1)
        self.assertEqual(Entitlement.objects.count(), 1)

    def test_unpaid_session_does_not_fulfil(self):
        order = create_order_for_product(self.product)
        self._post_webhook(self._event(order, payment_status="unpaid"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_invalid_signature_rejected(self):
        resp = self.client.post(reverse("payments:stripe_webhook"), data="{}", content_type="application/json")
        self.assertEqual(resp.status_code, 400)


class DownloadTests(BaseTestCase):
    def test_signed_link_downloads_and_logs(self):
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        resp = self.client.get(ent.get_absolute_url())
        self.assertContains(resp, "Kit")
        url = reverse("downloads:file", args=[ent.signed_token(), self.file.pk])
        resp = self.client.get(url)
        self.assertEqual(b"".join(resp.streaming_content), b"zipdata")
        self.assertEqual(DownloadLog.objects.count(), 1)

    def test_link_expires_after_ttl(self):
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        url = ent.get_absolute_url()
        later = timezone.now() + timedelta(hours=25)
        with mock.patch("django.core.signing.time.time", return_value=later.timestamp()):
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 410)
        self.assertContains(resp, "expired", status_code=410)

    def test_tampered_link_404(self):
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        resp = self.client.get(reverse("downloads:entitlement", args=[ent.signed_token() + "x"]))
        self.assertEqual(resp.status_code, 404)

    def test_download_limit_per_file(self):
        s = SiteSettings.load()
        s.download_limit = 2
        s.save()
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        url = reverse("downloads:file", args=[ent.signed_token(), self.file.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 410)

    def test_refunded_order_blocks_downloads(self):
        order = self.paid_order()
        ent = Entitlement.objects.get(order_item__order=order)
        order.status = Order.Status.REFUNDED
        order.save()
        self.assertEqual(self.client.get(ent.get_absolute_url()).status_code, 410)

    def test_latest_version_is_served(self):
        v2 = ProductFileVersion(product_file=self.file, version="2.0", changelog="New tabs")
        v2.file.save("kit-v2.zip", ContentFile(b"v2data"), save=True)
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        resp = self.client.get(reverse("downloads:file", args=[ent.signed_token(), self.file.pk]))
        self.assertEqual(b"".join(resp.streaming_content), b"v2data")

    @override_settings(USE_R2=True)
    def test_r2_mode_redirects_to_presigned_url(self):
        ent = Entitlement.objects.get(order_item__order=self.paid_order())
        with mock.patch.object(
            type(self.file.latest_version.file.storage), "url", return_value="https://r2.example/signed"
        ):
            resp = self.client.get(reverse("downloads:file", args=[ent.signed_token(), self.file.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://r2.example/signed")

    def test_notify_buyers_of_new_version(self):
        self.paid_order()
        self.paid_order()  # same email twice → one message
        mail.outbox.clear()
        sent = notify_buyers_of_update(self.file)
        self.assertEqual(sent, 1)
        self.assertIn("Update available", mail.outbox[0].subject)


class BundleTests(BaseTestCase):
    def test_bundle_grants_each_included_product(self):
        other = make_product("Policy Pack", self.cat, "79.00")
        add_file(other, "Policies")
        bundle = make_product("Complete Toolkit", self.cat, "149.00", product_type=Product.ProductType.BUNDLE)
        bundle.bundle_items.set([self.product, other])
        self.assertEqual(bundle.bundle_savings, Decimal("79.00"))
        order = self.paid_order(product=bundle)
        products = set(Entitlement.objects.filter(order_item__order=order).values_list("product__title", flat=True))
        self.assertEqual(products, {"ISO Kit", "Policy Pack"})


class StorefrontTests(BaseTestCase):
    def test_status_visibility(self):
        hidden = make_product("Hidden Kit", self.cat, status=Product.Status.HIDDEN)
        draft = make_product("Draft Kit", self.cat, status=Product.Status.DRAFT)
        future = make_product(
            "Future Kit", self.cat, status=Product.Status.SCHEDULED, publish_at=timezone.now() + timedelta(days=1)
        )
        listing = self.client.get(reverse("catalog:list")).content.decode()
        self.assertIn("ISO Kit", listing)
        for p in (hidden, draft, future):
            self.assertNotIn(p.title, listing)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(future.get_absolute_url()).status_code, 404)

    def test_filters_and_sorting(self):
        make_product("Cheap Checklist", self.cat, "19.00", product_type=Product.ProductType.PDF)
        resp = self.client.get(reverse("catalog:list"), {"max_price": "50", "sort": "price_asc"})
        titles = [p.title for p in resp.context["products"]]
        self.assertEqual(titles, ["Cheap Checklist"])
        resp = self.client.get(reverse("catalog:list"), {"type": "pdf"})
        self.assertEqual([p.title for p in resp.context["products"]], ["Cheap Checklist"])
        resp = self.client.get(reverse("catalog:list"), {"sort": "price_desc"})
        self.assertEqual(resp.context["products"][0].title, "ISO Kit")

    def test_htmx_returns_partial(self):
        resp = self.client.get(reverse("catalog:list"), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(resp, "catalog/_product_grid.html")
        self.assertTemplateNotUsed(resp, "base.html")

    def test_only_verified_buyers_can_review(self):
        user = get_user_model().objects.create_user("u", "u@example.com", "pw")
        self.client.force_login(user)
        url = reverse("reviews:submit", args=[self.product.slug])
        data = {"rating": 5, "title": "Great", "body": "Helpful"}
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.paid_order(user=user)
        resp = self.client.post(url, data)
        self.assertContains(resp, "Thanks")
        self.assertTrue(self.product.reviews.get().is_verified_purchase)
