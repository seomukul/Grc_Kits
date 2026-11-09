from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Service(TimeStampedModel):
    """A consulting offering, e.g. gap assessment, policy customisation, audit readiness."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=300)
    icon = models.CharField(
        max_length=20, default="shield",
        choices=[(i, i.title()) for i in ("shield", "bug", "audit", "scale", "risk", "training")],
    )
    description = models.TextField("overview", blank=True)
    deliverables = models.TextField(blank=True, help_text="One per line.")
    process_steps = models.TextField(blank=True, help_text="One per line: 'Step title | description'.")
    audience = models.TextField("who it's for", blank=True, help_text="One per line.")
    cta_label = models.CharField(max_length=40, default="Request a quote")
    meta_description = models.CharField(max_length=160, blank=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    frameworks = models.ManyToManyField("catalog.Framework", blank=True, related_name="services")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("services:detail", args=[self.slug])

    @property
    def deliverable_list(self):
        return _lines(self.deliverables)

    @property
    def audience_list(self):
        return _lines(self.audience)

    @property
    def process(self):
        return [[p.strip() for p in (row.split("|") + [""])[:2]] for row in _lines(self.process_steps)]


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


class ServiceFAQ(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


def private_storage():
    from django.core.files.storage import storages

    return storages["private"]


def inquiry_upload_path(instance, filename):
    import uuid

    return f"inquiries/{uuid.uuid4().hex}/{filename}"


class ServiceInquiry(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="inquiries")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    attachment = models.FileField(upload_to=inquiry_upload_path, storage=private_storage, blank=True, max_length=300)
    source = models.CharField(max_length=20, default="service", help_text="service page or contact page")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "service inquiries"

    def __str__(self):
        return f"{self.name} – {self.service or 'General'}"
