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
