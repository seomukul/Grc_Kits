from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.catalog.models import Category, Product
from apps.core.roles import EDITOR, ensure_roles
from apps.dashboard import analytics
from apps.orders.models import Customer, Order
from apps.orders.services import create_order_for_product, mark_order_paid

User = get_user_model()


def period(q):
    return analytics.resolve_period(QueryDict(q))


class AnalyticsTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Infosec", slug="infosec")
        self.p1 = Product.objects.create(title="Kit A", slug="a", category=cat, price=Decimal("100"), short_description="x", status="published")
        self.p2 = Product.objects.create(title="Kit B", slug="b", category=cat, price=Decimal("50"), short_description="x", status="published")

    def sale(self, product, days_ago=0, email="a@x.com", country="BD", fee="3.20", source=""):
        o = create_order_for_product(product)
        o.email, o.country, o.utm_source = email, country, source
        o.save()
        mark_order_paid(o, stripe_fee=Decimal(fee))
        Order.objects.filter(pk=o.pk).update(paid_at=timezone.now() - timedelta(days=days_ago))
        return Order.objects.get(pk=o.pk)

    def test_period_resolution(self):
        self.assertEqual(period("period=today").grain, "day")
        self.assertEqual(period("period=12m").grain, "month")
        p = period("period=custom&start=2026-01-01&end=2026-12-31")
        self.assertEqual((p.start_date.isoformat(), p.end_date.isoformat(), p.grain), ("2026-01-01", "2026-12-31", "month"))
        self.assertEqual(period("period=custom&start=bad").key, "custom")
        self.assertEqual(period("period=nonsense").key, "30d")

    def test_totals_net_and_change(self):
        self.sale(self.p1, 1)
        self.sale(self.p2, 2, email="b@x.com")
        refunded = self.sale(self.p2, 3, email="c@x.com")
        Order.objects.filter(pk=refunded.pk).update(status="refunded", refunded_amount=Decimal("50"))
        self.sale(self.p1, 40)  # previous period
        now, change = analytics.kpis(period("period=30d"))
        self.assertEqual(now["revenue"], Decimal("200"))
        self.assertEqual(now["orders"], 3)
        self.assertEqual(now["net"], Decimal("200") - Decimal("9.60") - Decimal("50"))
        self.assertEqual(now["aov"], Decimal("66.67"))
        self.assertEqual(change["revenue"], 100.0)

    def test_series_zero_fills_and_breakdowns(self):
        self.sale(self.p1, 0, country="US", source="linkedin")
        self.sale(self.p2, 0, email="b@x.com", country="US")
        p = period("period=7d")
        ser = analytics.series(p)
        self.assertEqual(len(ser["labels"]), 7)
        self.assertEqual(ser["revenue"][-1], 150.0)
        self.assertEqual(sum(ser["revenue"][:-1]), 0)
        self.assertEqual(analytics.top_products(p)[0]["product__title"], "Kit A")
        self.assertEqual(analytics.by_country(p)[0]["country"], "US")
        self.assertEqual({r["utm_source"] for r in analytics.by_source(p)}, {"linkedin", ""})

    def test_new_vs_returning(self):
        self.sale(self.p1, 60, email="old@x.com")
        self.sale(self.p2, 1, email="old@x.com")
        self.sale(self.p2, 1, email="new@x.com")
        self.assertEqual(analytics.customer_mix(period("period=30d")), {"new": 1, "returning": 1, "total": 2})

    def test_customers_kept_in_sync(self):
        with self.captureOnCommitCallbacks(execute=True):
            o = self.sale(self.p1, 0, email="Buyer@X.com")
        c = Customer.objects.get(email="buyer@x.com")
        self.assertEqual((c.orders_count, c.total_spent), (1, Decimal("100")))
        with self.captureOnCommitCallbacks(execute=True):
            o.refunded_amount = Decimal("100")
            o.status = "refunded"
            o.save()
        c.refresh_from_db()
        self.assertEqual(c.total_refunded, Decimal("100"))


@override_settings(ADMIN_2FA_REQUIRED=False)
class DashboardAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("owner", "o@x.com", "pw")
        self.editor = User.objects.create_user("ed", "e@x.com", "pw", is_staff=True)
        self.editor.groups.add(ensure_roles())

    def test_owner_sees_dashboard_and_exports(self):
        self.client.force_login(self.owner)
        resp = self.client.get("/admin/?period=7d")
        self.assertContains(resp, "Net revenue")
        self.assertContains(resp, "Last 7 days")
        for report in ("orders", "products", "countries", "sources", "summary"):
            r = self.client.get(reverse("dashboard:export", args=[report]) + "?period=30d")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(self.client.get(reverse("dashboard:export", args=["nope"])).status_code, 404)

    def test_editor_is_blog_only(self):
        self.client.force_login(self.editor)
        resp = self.client.get("/admin/")
        self.assertNotContains(resp, "Net revenue")
        self.assertEqual(self.client.get(reverse("dashboard:export", args=["orders"])).status_code, 403)
        self.assertEqual(self.client.get("/admin/orders/order/").status_code, 403)
        self.assertEqual(self.client.get("/admin/blog/post/").status_code, 200)
        self.assertEqual(self.client.get("/admin/blog/post/add/").status_code, 200)

    def test_customer_cannot_export(self):
        user = User.objects.create_user("c", "c@x.com", "pw")
        self.client.force_login(user)
        r = self.client.get(reverse("dashboard:export", args=["orders"]))
        self.assertEqual(r.status_code, 302)


@override_settings(ADMIN_2FA_REQUIRED=True, OTP_TOTP_THROTTLE_FACTOR=0, OTP_STATIC_THROTTLE_FACTOR=0)
class TwoFactorTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("owner", "o@x.com", "pw")
        self.client.force_login(self.owner)

    def test_first_login_requires_setup_then_works(self):
        resp = self.client.get("/admin/orders/order/")
        self.assertRedirects(resp, reverse("otp_setup") + "?next=/admin/orders/order/", fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("otp_setup")), "data:image/svg+xml")
        device = TOTPDevice.objects.get(user=self.owner)
        bad = self.client.post(reverse("otp_setup"), {"token": "000000"})
        self.assertContains(bad, "didn&#x27;t match")
        code = f"{totp(device.bin_key, device.step, device.t0, device.digits, device.drift):06d}"
        resp = self.client.post(reverse("otp_setup"), {"token": code})
        self.assertContains(resp, "backup codes")
        self.assertEqual(StaticToken.objects.filter(device__user=self.owner).count(), 8)
        self.assertEqual(self.client.get("/admin/orders/order/").status_code, 200)

    def test_returning_staff_verify_with_backup_code(self):
        TOTPDevice.objects.create(user=self.owner, name="phone", confirmed=True)
        static = StaticDevice.objects.create(user=self.owner, name="backup")
        StaticToken.objects.create(device=static, token="abcd1234")
        resp = self.client.get("/admin/")
        self.assertRedirects(resp, reverse("otp_verify") + "?next=/admin/", fetch_redirect_response=False)
        self.assertContains(self.client.post(reverse("otp_verify"), {"token": "wrong"}), "Invalid")
        resp = self.client.post(reverse("otp_verify"), {"token": "abcd1234", "next": "/admin/"})
        self.assertRedirects(resp, "/admin/", fetch_redirect_response=False)
        self.assertEqual(StaticToken.objects.count(), 0)  # single use

    def test_open_redirect_blocked(self):
        TOTPDevice.objects.create(user=self.owner, name="phone", confirmed=True)
        static = StaticDevice.objects.create(user=self.owner, name="backup")
        StaticToken.objects.create(device=static, token="abcd1234")
        resp = self.client.post(reverse("otp_verify"), {"token": "abcd1234", "next": "https://evil.example/"})
        self.assertRedirects(resp, "/admin/", fetch_redirect_response=False)

    @override_settings(OTP_TOTP_THROTTLE_FACTOR=1, OTP_STATIC_THROTTLE_FACTOR=1)
    def test_wrong_codes_are_throttled(self):
        TOTPDevice.objects.create(user=self.owner, name="phone", confirmed=True)
        self.client.post(reverse("otp_verify"), {"token": "111111"})
        resp = self.client.post(reverse("otp_verify"), {"token": "222222"})
        self.assertContains(resp, "Too many attempts")

    def test_storefront_and_customers_unaffected(self):
        self.assertEqual(self.client.get("/").status_code, 200)
