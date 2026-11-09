import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    email = models.EmailField(blank=True, db_index=True)
    name = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=2, blank=True, help_text="ISO country code from Stripe.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    currency = models.CharField(max_length=3, default=settings.STRIPE_CURRENCY)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    coupon = models.ForeignKey(
        "marketing.Coupon", null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    coupon_code = models.CharField(max_length=40, blank=True)

    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    invoice_url = models.URLField(max_length=500, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # First-touch attribution (traffic source) for reports.
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.short_number}"

    @property
    def short_number(self):
        return str(self.number)[:8].upper()

    @property
    def net_revenue(self):
        return self.total - self.stripe_fee - self.refunded_amount

    def get_absolute_url(self):
        return reverse("orders:detail", args=[self.number])

    def recalculate_totals(self):
        items = list(self.items.all())
        self.subtotal = sum((i.unit_price * i.quantity for i in items), Decimal("0"))
        self.discount_total = sum((i.discount for i in items), Decimal("0"))
        self.total = self.subtotal - self.discount_total
        return self.total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    # Snapshot so later product edits don't rewrite order history.
    product_title = models.CharField(max_length=200)
    license_tier = models.CharField(max_length=20, default="single")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="This line's share of the coupon discount."
    )

    def __str__(self):
        return f"{self.product_title} ({self.license_label}) × {self.quantity}"

    @property
    def license_label(self):
        from apps.catalog.models import LicenseTier

        return LicenseTier(self.license_tier).label

    @property
    def gross(self):
        return self.unit_price * self.quantity

    @property
    def line_total(self):
        return self.gross - self.discount
