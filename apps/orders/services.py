from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import LicenseTier
from apps.downloads.models import Entitlement

from .emails import send_order_confirmation
from .models import Order

ATTRIBUTION_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "referrer")


def _user_or_none(user):
    return user if user is not None and user.is_authenticated else None


def create_order_from_cart(cart, *, email, name="", user=None, attribution=None):
    """Create a pending order from the cart's current lines (prices and coupon re-validated)."""
    lines = cart.lines(email=email)
    if not lines:
        raise ValueError("Your cart is empty.")
    order = Order.objects.create(
        user=_user_or_none(user),
        email=email,
        name=name,
        currency=lines[0].product.currency,
        coupon=cart.coupon,
        coupon_code=cart.coupon.code if cart.coupon else "",
        **{k: (attribution or {}).get(k, "")[:100 if k != "referrer" else 500] for k in ATTRIBUTION_FIELDS},
    )
    for line in lines:
        order.items.create(
            product=line.product,
            product_title=line.product.title,
            license_tier=line.tier,
            unit_price=line.price,
            discount=line.discount,
        )
    order.recalculate_totals()
    order.save(update_fields=["subtotal", "discount_total", "total"])
    return order


def create_order_for_product(product, user=None, license_tier=LicenseTier.SINGLE):
    """Single-product order (used by tests and admin tools). Raises ValueError for tiers not offered."""
    price = product.price_for(license_tier)
    order = Order.objects.create(
        user=_user_or_none(user), email=getattr(user, "email", "") or "", currency=product.currency
    )
    order.items.create(
        product=product, product_title=product.title, license_tier=license_tier, unit_price=price
    )
    order.recalculate_totals()
    order.save(update_fields=["subtotal", "discount_total", "total"])
    return order


@transaction.atomic
def mark_order_paid(order, *, email="", name="", country="", payment_intent_id="", stripe_fee=None, invoice_url=""):
    """Idempotent: safe to call more than once for the same order (Stripe retries webhooks)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Order.Status.PAID:
        return order

    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.email = order.email or email
    order.name = order.name or name
    order.country = country or order.country
    order.stripe_payment_intent_id = payment_intent_id or order.stripe_payment_intent_id
    order.invoice_url = invoice_url or order.invoice_url
    if stripe_fee is not None:
        order.stripe_fee = stripe_fee
    if order.user_id is None and order.email:
        order.user = get_user_model().objects.filter(email__iexact=order.email).first()
    order.save()

    for item in order.items.select_related("product"):
        Entitlement.grant_for(item)

    transaction.on_commit(lambda: send_order_confirmation(order))
    return order


def claim_guest_orders(user):
    """Attach guest orders placed with this user's email to their account."""
    return Order.objects.filter(user__isnull=True, email__iexact=user.email).update(user=user)
