import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import storages
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel


def private_storage():
    return storages["private"]


def product_file_path(instance, filename):
    return f"products/{instance.product_id}/{uuid.uuid4().hex}/{filename}"


class ProductFile(TimeStampedModel):
    """A deliverable attached to a product. Stored outside the public media root."""

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="files")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=product_file_path, storage=private_storage)
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product} – {self.title} v{self.version}"


class Entitlement(TimeStampedModel):
    """A buyer's right to download the files of one purchased product."""

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.CASCADE, related_name="entitlements")
    download_count = models.PositiveIntegerField(default=0)
    max_downloads = models.PositiveIntegerField(default=settings.DOWNLOAD_LINK_MAX_USES)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order_item"], name="one_entitlement_per_order_item")]

    def __str__(self):
        return f"Entitlement {self.token}"

    @classmethod
    def grant(cls, order_item):
        expiry = timezone.now() + timedelta(days=settings.DOWNLOAD_LINK_EXPIRY_DAYS)
        obj, _ = cls.objects.get_or_create(order_item=order_item, defaults={"expires_at": expiry})
        return obj

    @property
    def product(self):
        return self.order_item.product

    @property
    def is_usable(self):
        if self.revoked or self.download_count >= self.max_downloads:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()

    def get_absolute_url(self):
        return reverse("downloads:entitlement", args=[self.token])
