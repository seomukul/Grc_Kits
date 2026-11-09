from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.core import magic_link
from apps.marketing import coupons as rules
from apps.marketing.models import Coupon
from apps.orders.models import Order
from apps.orders.services import create_order_for_product, mark_order_paid


def make_product(title, category, price):
    return Product.objects.create(
        title=title, slug=title.lower().replace(" ", "-"), category=category, price=Decimal(price),
        short_description="x", status=Product.Status.PUBLISHED,
    )


class CouponRuleTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="C", slug="c")
        self.a = make_product("A", cat, "100.00")
        self.b = make_product("B", cat, "50.00")
        self.lines = [rules.Line("a", self.a.pk, Decimal("100")), rules.Line("b", self.b.pk, Decimal("50"))]

    def test_percent_sitewide(self):
        c = Coupon.objects.create(code="p10", value=10)
        self.assertEqual(c.code, "P10")
        self.assertEqual(rules.allocate(c, self.lines), {"a": Decimal("10.00"), "b": Decimal("5.00")})

    def test_fixed_is_spread_proportionally_and_capped(self):
        c = Coupon.objects.create(code="F", value=30, discount_type="fixed")
        self.assertEqual(rules.allocate(c, self.lines), {"a": Decimal("20.00"), "b": Decimal("10.00")})
        big = Coupon.objects.create(code="BIG", value=500, discount_type="fixed")
        self.assertEqual(sum(rules.allocate(big, self.lines).values()), Decimal("150"))

    def test_product_specific(self):
        c = Coupon.objects.create(code="ONLYB", value=20)
        c.products.set([self.b])
        self.assertEqual(rules.allocate(c, self.lines), {"b": Decimal("10.00")})

    def test_validation_errors(self):
        cases = [
            Coupon(code="X1", value=10, is_active=False),
            Coupon(code="X2", value=10, valid_until=timezone.now() - timedelta(days=1)),
            Coupon(code="X3", value=10, valid_from=timezone.now() + timedelta(days=1)),
            Coupon(code="X4", value=10, min_order_amount=Decimal("500")),
        ]
        for c in cases:
            c.save()
            with self.assertRaises(rules.CouponError):
                rules.validate(c, self.lines)

    def test_max_uses_counts_paid_orders_only(self):
        c = Coupon.objects.create(code="LIM", value=10, max_uses=1)
        order = create_order_for_product(self.a)
        Order.objects.filter(pk=order.pk).update(coupon=c)
        rules.validate(c, self.lines)  # pending order doesn't count
        Order.objects.filter(pk=order.pk).update(status="paid")
        with self.assertRaises(rules.CouponError):
            rules.validate(c, self.lines)


class CartViewTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="C", slug="c")
        self.a = make_product("A Kit", cat, "100.00")

    def test_add_remove_and_badge_count(self):
        self.client.post(reverse("orders:cart_add", args=[self.a.slug]))
        resp = self.client.get(reverse("orders:cart"))
        self.assertContains(resp, "A Kit")
        self.assertEqual(resp.context["cart_count"], 1)
        resp = self.client.post(reverse("orders:cart_remove", args=[self.a.pk]), HTTP_HX_REQUEST="true")
        self.assertIn("cartChanged", resp["HX-Trigger"])
        self.assertContains(resp, "Your cart is empty")

    def test_invalid_coupon_shows_error(self):
        self.client.post(reverse("orders:cart_add", args=[self.a.slug]))
        resp = self.client.post(reverse("orders:cart_coupon"), {"code": "NOPE"}, HTTP_HX_REQUEST="true")
        self.assertContains(resp, "isn&#x27;t valid")

    def test_utm_attribution_saved_on_order(self):
        self.client.get("/?utm_source=linkedin&utm_campaign=launch")
        self.client.post(reverse("orders:cart_add", args=[self.a.slug]))
        from unittest import mock

        with mock.patch("apps.payments.views.get_client") as gc:
            gc.return_value.v1.checkout.sessions.create.return_value = mock.MagicMock(id="cs", url="https://x")
            self.client.post(reverse("payments:checkout"), {"email": "a@b.com", "accept_license": "on"})
        order = Order.objects.get()
        self.assertEqual((order.utm_source, order.utm_campaign), ("linkedin", "launch"))


class MagicLinkTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        cat = Category.objects.create(name="C", slug="c")
        self.product = make_product("Kit", cat, "10.00")
        self.order = create_order_for_product(self.product)
        self.order.email = "guest@example.com"
        self.order.save()
        mark_order_paid(self.order)
        mail.outbox.clear()

    def _link_from_email(self):
        return next(line for line in mail.outbox[-1].body.splitlines() if "/account/login/" in line).strip()

    def test_buyer_gets_link_account_created_and_orders_claimed(self):
        resp = self.client.post(reverse("account:login"), {"email": "Guest@Example.com"})
        self.assertContains(resp, "Check your email")
        url = self._link_from_email()
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse("dashboard:home"))
        user = get_user_model().objects.get(email="guest@example.com")
        self.order.refresh_from_db()
        self.assertEqual(self.order.user, user)
        self.assertContains(self.client.get(reverse("dashboard:home")), "Kit")

    def test_link_works_once(self):
        self.client.post(reverse("account:login"), {"email": "guest@example.com"})
        url = self._link_from_email()
        self.client.get(url)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 400)

    def test_unknown_email_gets_same_page_but_no_mail(self):
        resp = self.client.post(reverse("account:login"), {"email": "nobody@example.com"})
        self.assertContains(resp, "Check your email")
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(get_user_model().objects.filter(email="nobody@example.com").exists())

    def test_tampered_token_rejected(self):
        user = get_user_model().objects.create_user("x", "x@example.com")
        token = magic_link.make_token(user) + "a"
        self.assertEqual(self.client.get(reverse("account:verify", args=[token])).status_code, 400)

    def test_rate_limit(self):
        for _ in range(7):
            self.client.post(reverse("account:login"), {"email": "guest@example.com"})
        self.assertEqual(len(mail.outbox), 5)
