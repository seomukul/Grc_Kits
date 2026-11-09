from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Framework(TimeStampedModel):
    """A compliance framework a kit maps to, e.g. ISO 27001, SOC 2, HIPAA, NIST CSF."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:category", args=[self.slug])


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_active=True)


class Product(TimeStampedModel):
    class Format(models.TextChoices):
        TOOLKIT = "toolkit", "Toolkit (bundle)"
        POLICY = "policy", "Policy template"
        PROCEDURE = "procedure", "Procedure"
        SPREADSHEET = "spreadsheet", "Spreadsheet / register"
        CHECKLIST = "checklist", "Checklist"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    frameworks = models.ManyToManyField(Framework, blank=True, related_name="products")
    format = models.CharField(max_length=20, choices=Format.choices, default=Format.TOOLKIT)

    short_description = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    whats_included = models.TextField(blank=True, help_text="One item per line.")
    image = models.ImageField(upload_to="products/", blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.50"))])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default=settings.STRIPE_CURRENCY)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])

    @property
    def price_cents(self) -> int:
        return int((self.price * 100).quantize(Decimal("1")))

    @property
    def included_items(self):
        return [line.strip() for line in self.whats_included.splitlines() if line.strip()]
