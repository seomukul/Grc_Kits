from decimal import Decimal

from django.db import models

from apps.core.models import TimeStampedModel


class Subscriber(TimeStampedModel):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=50, blank=True, help_text="Where they signed up, e.g. footer, blog, kit page.")
    is_active = models.BooleanField(default=True)
    consent_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentage"
        FIXED = "fixed", "Fixed amount (USD)"

    code = models.CharField(max_length=40, unique=True, help_text="Customers type this. Not case-sensitive.")
    description = models.CharField(max_length=200, blank=True, help_text="Internal note.")
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="e.g. 20 for 20% or $20.")
    products = models.ManyToManyField(
        "catalog.Product", blank=True, related_name="coupons", help_text="Leave empty for a sitewide coupon."
    )
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Total paid orders. Blank = unlimited.")
    max_uses_per_customer = models.PositiveIntegerField(null=True, blank=True, default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def label(self):
        if self.discount_type == self.DiscountType.PERCENT:
            return f"{Decimal(self.value).normalize():f}% off"
        return f"${self.value} off"

    def times_used(self, email=None):
        qs = self.orders.filter(status="paid")
        if email:
            qs = qs.filter(email__iexact=email)
        return qs.count()
