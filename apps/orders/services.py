from django.db import transaction
from django.utils import timezone

from apps.catalog.models import LicenseTier
from apps.downloads.models import Entitlement

from .emails import send_order_confirmation

from .models import Order


def create_order_for_product(product, user=None, license_tier=LicenseTier.SINGLE):
    """Create a pending order for one product at the chosen license tier.

    Raises ValueError if the product doesn't offer that tier.
    """
    price = product.price_for(license_tier)
    order = Order.objects.create(
        user=user if user and user.is_authenticated else None,
        email=getattr(user, "email", "") or "",
        currency=product.currency,
    )
    order.items.create(
        product=product, product_title=product.title, license_tier=license_tier, unit_price=price, quantity=1
    )
    order.recalculate_total()
    order.save(update_fields=["total"])
    return order


@transaction.atomic
def mark_order_paid(order, *, email="", payment_intent_id=""):
    """Idempotent: safe to call more than once for the same order (Stripe retries webhooks)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Order.Status.PAID:
        return order

    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    if email and not order.email:
        order.email = email
    if payment_intent_id:
        order.stripe_payment_intent_id = payment_intent_id
    order.save()

    for item in order.items.select_related("product"):
        Entitlement.grant_for(item)

    transaction.on_commit(lambda: send_order_confirmation(order))
    return order
