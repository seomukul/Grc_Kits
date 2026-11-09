from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Page(TimeStampedModel):
    """Simple CMS page: about, terms, privacy, refund policy, etc."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField(help_text="HTML allowed. Only staff can edit this.")
    is_published = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=False)
    meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("pages:page", args=[self.slug])
