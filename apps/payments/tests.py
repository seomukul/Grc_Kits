import json
import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.downloads.models import Entitlement, ProductFile
from apps.orders.models import Order
from apps.orders.services import create_order_for_product
from apps.payments.models import StripeEvent

TMP = tempfile.mkdtemp()


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP}},
        "private": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": TMP}},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class CheckoutFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        cat = Category.objects.create(name="Toolkits", slug="toolkits")
        self.product = Product.objects.create(
            title="ISO Kit", slug="iso-kit", category=cat, price=Decimal("149.00"), short_description="x"
        )
        pf = ProductFile(product=self.product, title="Kit")
        pf.file.save("kit.zip", ContentFile(b"zipdata"), save=True)

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
                reverse("payments:stripe_webhook"),
                data=json.dumps(event),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=x",
            )

    def test_checkout_redirects_to_stripe(self):
        session = mock.MagicMock(id="cs_test_1", url="https://checkout.stripe.com/c/pay/cs_test_1")
        with mock.patch("apps.payments.views.get_client") as gc:
            gc.return_value.v1.checkout.sessions.create.return_value = session
            resp = self.client.post(reverse("payments:create", args=[self.product.slug]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], session.url)
        order = Order.objects.get()
        self.assertEqual(order.stripe_checkout_session_id, "cs_test_1")
        params = gc.return_value.v1.checkout.sessions.create.call_args.kwargs["params"]
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 14900)

    def test_webhook_marks_paid_grants_download_and_emails(self):
        order = create_order_for_product(self.product)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_webhook(self._event(order))
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.email, "buyer@example.com")
        ent = Entitlement.objects.get(order_item__order=order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(ent.token), mail.outbox[0].body)

        file_id = self.product.files.get().pk
        resp = self.client.get(reverse("downloads:file", args=[ent.token, file_id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"zipdata")
        ent.refresh_from_db()
        self.assertEqual(ent.download_count, 1)

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

    def test_download_blocked_for_unpaid_order(self):
        order = create_order_for_product(self.product)
        ent = Entitlement.grant(order.items.get())
        resp = self.client.get(reverse("downloads:entitlement", args=[ent.token]))
        self.assertEqual(resp.status_code, 404)
