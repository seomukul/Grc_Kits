from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Service(TimeStampedModel):
    """A consulting offering, e.g. gap assessment, policy customisation, audit readiness."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=300)
    description = models.TextField(blank=True)
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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "service inquiries"

    def __str__(self):
        return f"{self.name} – {self.service or 'General'}"
