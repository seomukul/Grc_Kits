from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SiteSettings, TimeStampedModel


class Framework(TimeStampedModel):
    """A compliance framework a kit maps to, e.g. ISO 27001, SOC 2, PCI DSS, BB CSF."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    ICONS = ["shield", "lock", "scale", "audit", "risk", "training", "globe", "badge"]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=20, default="shield", choices=[(i, i.title()) for i in ICONS])
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:category", args=[self.slug])


class ProductQuerySet(models.QuerySet):
    def listed(self):
        """Shown in the shop, search, home page and sitemap."""
        now = timezone.now()
        return self.filter(
            Q(status=Product.Status.PUBLISHED) | Q(status=Product.Status.SCHEDULED, publish_at__lte=now)
        )

    def purchasable(self):
        """Listed products plus hidden (unlisted, direct-link only) products."""
        now = timezone.now()
        return self.filter(
            Q(status__in=[Product.Status.PUBLISHED, Product.Status.HIDDEN])
            | Q(status=Product.Status.SCHEDULED, publish_at__lte=now)
        )

    def with_recent_sales(self, days=30):
        since = timezone.now() - timedelta(days=days)
        return self.annotate(
            recent_sales=Count(
                "order_items",
                filter=Q(order_items__order__status="paid", order_items__order__paid_at__gte=since),
                distinct=True,
            )
        )

    def with_total_sales(self):
        return self.annotate(
            total_sales=Count("order_items", filter=Q(order_items__order__status="paid"), distinct=True)
        )


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden (unlisted, link only)"
        SCHEDULED = "scheduled", "Scheduled"

    class ProductType(models.TextChoices):
        EXCEL = "excel", "Excel tool"
        WORD = "word", "Word template"
        PDF = "pdf", "PDF"
        BUNDLE = "bundle", "Bundle"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    frameworks = models.ManyToManyField(Framework, blank=True, related_name="products")
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.EXCEL)

    short_description = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    whats_included = models.TextField(blank=True, help_text="One item per line.")
    system_requirements = models.CharField(max_length=200, blank=True, help_text="e.g. Microsoft Excel 2016 or later")

    cover_label = models.CharField(
        max_length=40, blank=True,
        help_text="Big text on the product card cover, e.g. 'ISO/IEC 27001:2022'. Defaults to the first framework.",
    )
    image = models.ImageField(
        "cover image", upload_to="products/covers/", blank=True,
        help_text="Optional. Without an image the card shows a designed cover with the label above.",
    )
    preview_video_url = models.URLField(blank=True, help_text="YouTube or Vimeo link.")
    sample_file = models.FileField(
        upload_to="products/samples/", blank=True, help_text="Public sample (e.g. a few PDF pages) buyers can view."
    )

    price = models.DecimalField(
        "price (single user)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.50"))],
    )
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default=settings.STRIPE_CURRENCY)

    # Bundles: a product of type "bundle" sells several other products together.
    bundle_items = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="included_in_bundles",
        limit_choices_to=~Q(product_type="bundle"),
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    publish_at = models.DateTimeField(null=True, blank=True, help_text="Required for Scheduled.")
    is_featured = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    og_image = models.ImageField("social share image", upload_to="products/og/", blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.status == self.Status.SCHEDULED and not self.publish_at:
            raise ValidationError({"publish_at": "Set a publish date for scheduled products."})

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])

    # --- state helpers -------------------------------------------------
    @property
    def is_bundle(self):
        return self.product_type == self.ProductType.BUNDLE

    @property
    def is_listed(self):
        if self.status == self.Status.PUBLISHED:
            return True
        return self.status == self.Status.SCHEDULED and self.publish_at and self.publish_at <= timezone.now()

    def is_new(self, site_settings=None):
        s = site_settings or SiteSettings.load()
        return self.created_at >= timezone.now() - timedelta(days=s.new_badge_days)

    def is_bestseller(self, site_settings=None):
        sales = getattr(self, "recent_sales", None)
        if sales is None:
            return False
        s = site_settings or SiteSettings.load()
        return sales >= s.bestseller_min_sales

    @property
    def cover_text(self):
        if self.cover_label:
            return self.cover_label
        fw = next(iter(self.frameworks.all()), None)
        return fw.name if fw else self.title

    @property
    def included_items(self):
        return [line.strip() for line in self.whats_included.splitlines() if line.strip()]

    @property
    def video_embed_url(self):
        url = self.preview_video_url
        if "youtube.com/watch?v=" in url:
            return "https://www.youtube-nocookie.com/embed/" + url.split("v=")[1].split("&")[0]
        if "youtu.be/" in url:
            return "https://www.youtube-nocookie.com/embed/" + url.rsplit("/", 1)[1].split("?")[0]
        if "vimeo.com/" in url:
            return "https://player.vimeo.com/video/" + url.rstrip("/").rsplit("/", 1)[1]
        return ""

    # --- bundles -------------------------------------------------------
    def deliverable_products(self):
        """Products whose files a buyer of this product gets."""
        if self.is_bundle:
            return list(self.bundle_items.all())
        return [self]

    @property
    def bundle_value(self):
        """Sum of the single-user prices of the bundled products."""
        return sum((p.price for p in self.bundle_items.all()), Decimal("0"))

    @property
    def bundle_savings(self):
        value = self.bundle_value
        return value - self.price if value > self.price else Decimal("0")

    # --- license tiers -------------------------------------------------
    def license_options(self, site_settings=None):
        """[(tier, label, price, description), ...] starting with Single user."""
        s = site_settings or SiteSettings.load()
        options = [(LicenseTier.SINGLE, LicenseTier.SINGLE.label, self.price, "1 user")]
        for lic in self.licenses.filter(is_active=True):
            options.append((lic.tier, lic.get_tier_display(), lic.effective_price(s), lic.description(s)))
        order = list(LicenseTier.values)
        return sorted(options, key=lambda o: order.index(o[0]))

    def price_for(self, tier, site_settings=None):
        for t, _label, price, _desc in self.license_options(site_settings):
            if t == tier:
                return price
        raise ValueError(f"License tier {tier!r} is not offered for {self}")


class LicenseTier(models.TextChoices):
    SINGLE = "single", "Single user"
    TEAM = "team", "Team"
    ORGANIZATION = "organization", "Organization"


class ProductLicense(models.Model):
    """An extra license tier offered for a product. Single user is always offered at Product.price."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="licenses")
    tier = models.CharField(
        max_length=20, choices=[c for c in LicenseTier.choices if c[0] != LicenseTier.SINGLE]
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Leave blank to use the multiplier from Site settings.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "tier"], name="one_license_per_tier")]

    def __str__(self):
        return f"{self.product} – {self.get_tier_display()}"

    def effective_price(self, site_settings=None):
        if self.price is not None:
            return self.price
        s = site_settings or SiteSettings.load()
        mult = s.team_price_multiplier if self.tier == LicenseTier.TEAM else s.organization_price_multiplier
        return (self.product.price * mult).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def description(self, site_settings=None):
        s = site_settings or SiteSettings.load()
        if self.tier == LicenseTier.TEAM:
            return f"Up to {s.team_max_users} users in one organization"
        return "Unlimited users in one organization"


class ProductImage(models.Model):
    """Gallery images and screenshots."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/gallery/")
    alt = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.alt or f"Image {self.pk}"


class ProductFAQ(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


def cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
