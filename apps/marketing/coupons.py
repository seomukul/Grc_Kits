"""Coupon validation and discount allocation.

Discounts are calculated here (our rules), stored per order line, and shown in Stripe
Checkout as a one-off Stripe coupon for the exact total discount.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from django.utils import timezone

from .models import Coupon

CENT = Decimal("0.01")


class CouponError(Exception):
    pass


@dataclass
class Line:
    """Anything with a product and a gross price, e.g. a cart line or an OrderItem."""

    key: str
    product_id: int
    gross: Decimal


def find_coupon(code):
    code = (code or "").strip().upper()
    if not code:
        raise CouponError("Enter a coupon code.")
    try:
        return Coupon.objects.prefetch_related("products").get(code=code)
    except Coupon.DoesNotExist:
        raise CouponError("That coupon code isn't valid.")


def validate(coupon, lines, email=None):
    """Raise CouponError if the coupon can't be used for these lines."""
    now = timezone.now()
    if not coupon.is_active:
        raise CouponError("This coupon is no longer active.")
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponError("This coupon isn't active yet.")
    if coupon.valid_until and now > coupon.valid_until:
        raise CouponError("This coupon has expired.")
    if coupon.max_uses is not None and coupon.times_used() >= coupon.max_uses:
        raise CouponError("This coupon has reached its usage limit.")
    if email and coupon.max_uses_per_customer is not None:
        if coupon.times_used(email=email) >= coupon.max_uses_per_customer:
            raise CouponError("You've already used this coupon.")
    subtotal = sum((line.gross for line in lines), Decimal("0"))
    if coupon.min_order_amount and subtotal < coupon.min_order_amount:
        raise CouponError(f"This coupon needs a minimum order of ${coupon.min_order_amount}.")
    if not eligible(coupon, lines):
        raise CouponError("This coupon doesn't apply to the items in your cart.")


def eligible(coupon, lines):
    allowed = {p.pk for p in coupon.products.all()}
    return [line for line in lines if not allowed or line.product_id in allowed]


def allocate(coupon, lines):
    """Return {line.key: discount} for eligible lines. Never discounts a line below zero."""
    targets = eligible(coupon, lines)
    base = sum((line.gross for line in targets), Decimal("0"))
    if base <= 0:
        return {}
    if coupon.discount_type == Coupon.DiscountType.PERCENT:
        pct = min(Decimal(coupon.value), Decimal("100")) / 100
        return {line.key: (line.gross * pct).quantize(CENT, rounding=ROUND_DOWN) for line in targets}

    # Fixed amount: spread over eligible lines in proportion to price; last line takes the rounding.
    total = min(Decimal(coupon.value), base)
    result, remaining = {}, total
    for i, line in enumerate(targets):
        if i == len(targets) - 1:
            share = remaining
        else:
            share = (total * line.gross / base).quantize(CENT, rounding=ROUND_DOWN)
        share = min(share, line.gross)
        result[line.key] = share
        remaining -= share
    return result
