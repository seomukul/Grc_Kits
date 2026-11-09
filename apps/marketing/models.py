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
