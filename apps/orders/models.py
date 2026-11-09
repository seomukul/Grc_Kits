import uuid

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
        CANCELLED = "cancelled", "Cancelled"

    number = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    currency = models.CharField(max_length=3, default=settings.STRIPE_CURRENCY)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {str(self.number)[:8]}"

    @property
    def short_number(self):
        return str(self.number)[:8].upper()

    def get_absolute_url(self):
        return reverse("orders:detail", args=[self.number])

    def recalculate_total(self):
        self.total = sum((item.line_total for item in self.items.all()), start=0)
        return self.total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    # Snapshot so later product edits don't rewrite order history.
    product_title = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product_title} × {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
