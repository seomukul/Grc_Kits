from django.db import migrations
from django.db.models import Count, Max, Min, Sum

SALE_STATUSES = ["paid", "refunded", "disputed"]


def backfill(apps, schema_editor):
    """Uses historical models only, so it keeps working after later schema changes."""
    Order = apps.get_model("orders", "Order")
    Customer = apps.get_model("orders", "Customer")
    rows = (
        Order.objects.filter(status__in=SALE_STATUSES).exclude(email="")
        .values("email").annotate(n=Count("id"), spent=Sum("total"), refunded=Sum("refunded_amount"),
                                  first=Min("paid_at"), last=Max("paid_at"))
    )
    merged = {}
    for r in rows:
        key = r["email"].lower()
        m = merged.setdefault(key, {"n": 0, "spent": 0, "refunded": 0, "first": r["first"], "last": r["last"]})
        m["n"] += r["n"]; m["spent"] += r["spent"] or 0; m["refunded"] += r["refunded"] or 0
        m["first"] = min(filter(None, [m["first"], r["first"]]), default=None)
        m["last"] = max(filter(None, [m["last"], r["last"]]), default=None)
    for email, m in merged.items():
        latest = Order.objects.filter(email__iexact=email, status__in=SALE_STATUSES).order_by("-paid_at").first()
        Customer.objects.update_or_create(email=email, defaults={
            "name": latest.name, "country": latest.country, "user_id": latest.user_id,
            "orders_count": m["n"], "total_spent": m["spent"], "total_refunded": m["refunded"],
            "first_order_at": m["first"], "last_order_at": m["last"],
        })


class Migration(migrations.Migration):
    dependencies = [("orders", "0003_customer")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
