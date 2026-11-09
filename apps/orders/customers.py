from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, Max, Min, Sum, Value
from django.db.models.functions import Coalesce

from .models import Customer, Order

SALE_STATUSES = [Order.Status.PAID, Order.Status.REFUNDED, Order.Status.DISPUTED]
MONEY = DecimalField(max_digits=12, decimal_places=2)


def refresh_customer(email):
    """Recalculate one customer's totals from their orders. Safe to call any time."""
    if not email:
        return None
    from apps.marketing.models import Subscriber

    email = email.lower()
    sales = Order.objects.filter(email__iexact=email, status__in=SALE_STATUSES)
    agg = sales.aggregate(
        n=Count("id"),
        spent=Coalesce(Sum("total"), Value(0), output_field=MONEY),
        refunded=Coalesce(Sum("refunded_amount"), Value(0), output_field=MONEY),
        first=Min("paid_at"),
        last=Max("paid_at"),
    )
    if not agg["n"]:
        Customer.objects.filter(email=email).delete()
        return None
    latest = sales.order_by("-paid_at").first()
    customer, _ = Customer.objects.update_or_create(
        email=email,
        defaults={
            "name": latest.name or "",
            "country": latest.country or "",
            "user": latest.user or get_user_model().objects.filter(email__iexact=email).first(),
            "orders_count": agg["n"],
            "total_spent": agg["spent"],
            "total_refunded": agg["refunded"],
            "first_order_at": agg["first"],
            "last_order_at": agg["last"],
            "is_subscriber": Subscriber.objects.filter(email__iexact=email, is_active=True).exists(),
        },
    )
    return customer


def rebuild_all():
    emails = set(
        e.lower() for e in Order.objects.filter(status__in=SALE_STATUSES).exclude(email="").values_list("email", flat=True)
    )
    for email in emails:
        refresh_customer(email)
    Customer.objects.exclude(email__in=emails).delete()
    return len(emails)
