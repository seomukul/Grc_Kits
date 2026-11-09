from django.db import models


class StripeEvent(models.Model):
    """Every processed webhook event, for idempotency and auditing."""

    event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField()
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.type} ({self.event_id})"
