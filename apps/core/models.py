from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    """Custom user from day one, so we can extend it later without a painful migration."""

    email = models.EmailField("email address", unique=True)
    company = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.email or self.username


class SiteSettings(models.Model):
    """Singleton for settings the owner changes from the admin (no deploy needed)."""

    # Downloads
    download_limit = models.PositiveIntegerField(default=5, help_text="Downloads allowed per purchased product.")
    download_link_ttl_hours = models.PositiveIntegerField(default=24, help_text="How long a download link stays valid.")

    # License tiers (defaults used when a product's tier price is left blank)
    team_price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=2)
    organization_price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    team_max_users = models.PositiveIntegerField(default=10)

    # Storefront badges
    new_badge_days = models.PositiveIntegerField(default=30, help_text="Products created within this many days show 'New'.")
    bestseller_min_sales = models.PositiveIntegerField(
        default=5, help_text="Units sold in the last 30 days for the 'Bestseller' badge."
    )

    # Checkout
    stripe_invoices = models.BooleanField(
        default=True,
        help_text="Have Stripe create a PDF invoice for every order (Stripe charges a small invoicing fee).",
    )

    class Meta:
        verbose_name = verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - singleton is never deleted
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
