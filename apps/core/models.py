from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
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

    # Shown in the blog author box.
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    linkedin_url = models.URLField(blank=True)

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

    # Abandoned checkout reminders
    abandoned_cart_emails = models.BooleanField(
        default=False,
        help_text="Email people who started checkout but didn't pay (one reminder). Check this is allowed where you sell.",
    )
    abandoned_cart_delay_hours = models.PositiveIntegerField(default=2)

    # Business identity (shown in the footer and on legal pages; Stripe checks these)
    legal_name = models.CharField(
        "legal business name", max_length=150, default="GRCkits",
        help_text="Exactly as registered, e.g. 'GRCkits LLC'. Must match your Stripe account.",
    )
    registration = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. 'Registered in Wyoming, USA' or 'Company no. 12345678'.",
    )
    business_address = models.TextField(blank=True, help_text="Full registered/business address.")
    governing_law = models.CharField(
        max_length=120, blank=True, help_text="Used in the Terms, e.g. 'the State of Wyoming, USA'.",
    )
    support_phone = models.CharField(max_length=40, blank=True, help_text="Optional, e.g. +1 (555) 123-4567.")
    support_hours = models.CharField(max_length=120, default="Mon–Fri, 9:00–18:00 (GMT+6)")
    footer_disclaimer = models.TextField(
        blank=True,
        default=(
            "GRCkits templates and toolkits are provided for guidance and must be tailored to your organization. "
            "They do not constitute legal advice and do not guarantee certification or regulatory compliance."
        ),
    )

    # Contact & social
    contact_email = models.EmailField(default="hello@grckits.com")
    response_time_note = models.CharField(max_length=120, default="We reply within one business day.")
    linkedin_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    x_url = models.URLField("X / Twitter URL", blank=True)
    youtube_url = models.URLField(blank=True)
    booking_url = models.URLField(
        blank=True, help_text="Calendly or Cal.com link for discovery calls (shown on service and contact pages)."
    )

    # Analytics & tracking (loaded only after the visitor accepts cookies)
    ga4_measurement_id = models.CharField(
        "GA4 measurement ID", max_length=20, blank=True, help_text="e.g. G-XXXXXXXXXX",
        validators=[RegexValidator(r"^G-[A-Z0-9]{4,16}$", "Looks like G-XXXXXXXXXX")],
    )
    search_console_verification = models.CharField(
        max_length=100, blank=True, help_text="Only the content value of Google's <meta name=\"google-site-verification\"> tag.",
        validators=[RegexValidator(r"^[A-Za-z0-9_-]+$", "Paste only the token value.")],
    )
    meta_pixel_id = models.CharField(
        "Meta pixel ID", max_length=20, blank=True, validators=[RegexValidator(r"^\d{6,20}$", "Digits only.")]
    )
    linkedin_partner_id = models.CharField(
        "LinkedIn Insight partner ID", max_length=20, blank=True, validators=[RegexValidator(r"^\d{3,20}$", "Digits only.")]
    )

    # Newsletter lead magnet
    lead_magnet_title = models.CharField(max_length=120, blank=True, help_text="e.g. Free ISO 27001 Policy Sample")
    lead_magnet_file = models.FileField(upload_to="lead-magnets/", blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "site settings"

    @property
    def stripe_ready_missing(self):
        """Business details Stripe reviewers expect to see on the site that are still empty."""
        checks = {
            "Legal business name": self.legal_name and self.legal_name != "GRCkits",
            "Business address": self.business_address,
            "Contact email": self.contact_email,
        }
        return [label for label, ok in checks.items() if not ok]

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
