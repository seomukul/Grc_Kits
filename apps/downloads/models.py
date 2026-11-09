import uuid

from django.core import signing
from django.core.files.storage import storages
from django.db import models
from django.urls import reverse

from apps.core.models import SiteSettings, TimeStampedModel

SIGNING_SALT = "grckits.downloads"


def private_storage():
    return storages["private"]


def version_file_path(instance, filename):
    product_id = instance.product_file.product_id
    return f"products/{product_id}/{uuid.uuid4().hex}/{filename}"


class ProductFile(TimeStampedModel):
    """One deliverable of a product (e.g. 'Risk Register.xlsx'). Its content lives in versions."""

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="files")
    title = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product} – {self.title}"

    @property
    def latest_version(self):
        return self.versions.order_by("-created_at").first()


class ProductFileVersion(models.Model):
    """An uploaded version of a deliverable. Buyers always get the latest one."""

    product_file = models.ForeignKey(ProductFile, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=20, default="1.0")
    file = models.FileField(upload_to=version_file_path, storage=private_storage, max_length=500)
    changelog = models.TextField(blank=True, help_text="What changed in this version (shown to buyers).")
    size = models.PositiveBigIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product_file", "version"], name="unique_version_per_file")
        ]

    def __str__(self):
        return f"{self.product_file.title} v{self.version}"

    def save(self, *args, **kwargs):
        if self.file and not self.size:
            try:
                self.size = self.file.size
            except Exception:  # pragma: no cover - remote storage hiccup shouldn't block saving
                self.size = 0
        super().save(*args, **kwargs)

    @property
    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]


class Entitlement(TimeStampedModel):
    """A buyer's right to download one product's files, created when an order is paid.

    A bundle purchase creates one entitlement per bundled product.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.CASCADE, related_name="entitlements")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="entitlements")
    max_downloads = models.PositiveIntegerField(help_text="Per file.")
    revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["order_item", "product"], name="one_entitlement_per_item_product")
        ]

    def __str__(self):
        return f"{self.product} for order {self.order_item.order.short_number}"

    @classmethod
    def grant_for(cls, order_item):
        """Create entitlements for everything the order item delivers. Idempotent."""
        limit = SiteSettings.load().download_limit
        return [
            cls.objects.get_or_create(order_item=order_item, product=p, defaults={"max_downloads": limit})[0]
            for p in order_item.product.deliverable_products()
        ]

    @property
    def order(self):
        return self.order_item.order

    @property
    def is_active(self):
        return not self.revoked and self.order.status == "paid"

    def downloads_used(self, product_file):
        return self.logs.filter(product_file=product_file).count()

    def can_download(self, product_file):
        return self.is_active and self.downloads_used(product_file) < self.max_downloads

    # --- signed, expiring links -----------------------------------------
    def signed_token(self):
        return signing.TimestampSigner(salt=SIGNING_SALT).sign(str(self.token))

    @staticmethod
    def unsign(value, max_age_hours):
        """Return the entitlement UUID string, or raise signing.BadSignature / SignatureExpired."""
        return signing.TimestampSigner(salt=SIGNING_SALT).unsign(value, max_age=max_age_hours * 3600)

    def get_absolute_url(self):
        """A fresh link valid for SiteSettings.download_link_ttl_hours from now."""
        return reverse("downloads:entitlement", args=[self.signed_token()])


class DownloadLog(models.Model):
    entitlement = models.ForeignKey(Entitlement, on_delete=models.CASCADE, related_name="logs")
    product_file = models.ForeignKey(ProductFile, on_delete=models.CASCADE, related_name="download_logs")
    version = models.ForeignKey(ProductFileVersion, null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
