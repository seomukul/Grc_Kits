"""Fake sales history for trying out the dashboard locally. Refuses to run with DEBUG off."""

import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalog.models import LicenseTier, Product
from apps.downloads.models import Entitlement
from apps.orders.models import Order

COUNTRIES = ["US", "GB", "BD", "CA", "AU", "DE", "AE", "IN", "SG", "NL"]
SOURCES = ["", "", "google", "linkedin", "newsletter", "chatgpt.com"]


class Command(BaseCommand):
    help = "Create fake paid orders over the last 12 months (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--orders", type=int, default=150)

    def handle(self, *args, orders, **options):
        if not settings.DEBUG:
            raise CommandError("seed_sales only runs with DEBUG=True.")
        products = list(Product.objects.listed())
        if not products:
            raise CommandError("Run seed_demo first.")
        rng = random.Random(42)
        now = timezone.now()
        emails = [f"buyer{i}@example.com" for i in range(int(orders * 0.7))]
        for _ in range(orders):
            paid_at = now - timedelta(days=rng.betavariate(1.2, 2.5) * 365, hours=rng.random() * 24)
            order = Order.objects.create(
                email=rng.choice(emails), country=rng.choice(COUNTRIES), utm_source=rng.choice(SOURCES),
                status=Order.Status.PAID, paid_at=paid_at,
            )
            for p in rng.sample(products, k=rng.choice([1, 1, 1, 2])):
                tier = rng.choices([LicenseTier.SINGLE, LicenseTier.TEAM, LicenseTier.ORGANIZATION], [8, 2, 1])[0]
                try:
                    price = p.price_for(tier)
                except ValueError:
                    tier, price = LicenseTier.SINGLE, p.price
                item = order.items.create(product=p, product_title=p.title, license_tier=tier, unit_price=price)
                Entitlement.grant_for(item)
            if rng.random() < 0.15:
                order.coupon_code = "LAUNCH20"
                for item in order.items.all():
                    item.discount = (item.unit_price * Decimal("0.2")).quantize(Decimal("0.01"))
                    item.save()
            order.recalculate_totals()
            order.stripe_fee = (order.total * Decimal("0.029") + Decimal("0.30")).quantize(Decimal("0.01"))
            roll = rng.random()
            if roll < 0.03:
                order.status, order.refunded_amount = Order.Status.REFUNDED, order.total
            elif roll < 0.04:
                order.status = Order.Status.DISPUTED
            order.save()
            Order.objects.filter(pk=order.pk).update(created_at=paid_at - timedelta(minutes=3))
        # Some abandoned checkouts for the conversion card.
        for _ in range(orders // 3):
            o = Order.objects.create(email=rng.choice(emails), status=Order.Status.CANCELLED)
            Order.objects.filter(pk=o.pk).update(created_at=now - timedelta(days=rng.random() * 365))
        self.stdout.write(self.style.SUCCESS(f"Created {orders} fake paid orders."))
