from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order


@receiver(post_save, sender=Order)
def sync_customer(sender, instance, **kwargs):
    if instance.email and instance.status != Order.Status.PENDING:
        from .customers import refresh_customer

        email = instance.email
        transaction.on_commit(lambda: refresh_customer(email))
