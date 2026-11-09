"""Sales analytics for the admin dashboard and CSV exports.

All money figures are in USD (the store currency). A "sale" is an order that was paid,
including ones later refunded or disputed: refunds are subtracted in *net revenue*.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Min, Q, Sum
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

from apps.orders.models import Order, OrderItem

SALE_STATUSES = [Order.Status.PAID, Order.Status.REFUNDED, Order.Status.DISPUTED]
ZERO = Decimal("0")
MONEY = DecimalField(max_digits=12, decimal_places=2)

PRESETS = {
    "today": "Today",
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "month": "This month",
    "12m": "Last 12 months",
    "year": "This year",
    "custom": "Custom range",
}


@dataclass
class Period:
    key: str
    start: datetime  # inclusive
    end: datetime  # exclusive
    grain: str  # day | week | month

    @property
    def label(self):
        return PRESETS.get(self.key, "Custom range")

    @property
    def previous(self):
        length = self.end - self.start
        return Period("prev", self.start - length, self.start, self.grain)

    @property
    def start_date(self):
        return timezone.localtime(self.start).date()

    @property
    def end_date(self):
        return (timezone.localtime(self.end) - timedelta(seconds=1)).date()


def _midnight(d: date):
    return timezone.make_aware(datetime.combine(d, time.min))


def resolve_period(params) -> Period:
    """Build a Period from GET params: ?period=30d or ?period=custom&start=YYYY-MM-DD&end=YYYY-MM-DD."""
    key = params.get("period") or "30d"
    today = timezone.localdate()
    tomorrow = _midnight(today + timedelta(days=1))
    if key == "today":
        return Period(key, _midnight(today), tomorrow, "day")
    if key == "7d":
        return Period(key, _midnight(today - timedelta(days=6)), tomorrow, "day")
    if key == "month":
        return Period(key, _midnight(today.replace(day=1)), tomorrow, "day")
    if key == "12m":
        first = (today.replace(day=1) - timedelta(days=335)).replace(day=1)
        return Period(key, _midnight(first), tomorrow, "month")
    if key == "year":
        return Period(key, _midnight(today.replace(month=1, day=1)), tomorrow, "month")
    if key == "custom":
        try:
            start = date.fromisoformat(params.get("start", ""))
            end = date.fromisoformat(params.get("end", ""))
        except ValueError:
            start, end = today - timedelta(days=29), today
        if end < start:
            start, end = end, start
        days = (end - start).days + 1
        grain = "day" if days <= 62 else "week" if days <= 26 * 7 else "month"
        return Period(key, _midnight(start), _midnight(end + timedelta(days=1)), grain)
    return Period("30d", _midnight(today - timedelta(days=29)), tomorrow, "day")


# --- querysets ----------------------------------------------------------------

def sales(period):
    return Order.objects.filter(status__in=SALE_STATUSES, paid_at__gte=period.start, paid_at__lt=period.end)


def sale_items(period):
    return OrderItem.objects.filter(
        order__status__in=SALE_STATUSES, order__paid_at__gte=period.start, order__paid_at__lt=period.end
    ).annotate(
        revenue=ExpressionWrapper(F("unit_price") * F("quantity") - F("discount"), output_field=MONEY)
    )


# --- KPIs -----------------------------------------------------------------------

def totals(period):
    agg = sales(period).aggregate(
        revenue=Coalesce(Sum("total"), ZERO, output_field=MONEY),
        fees=Coalesce(Sum("stripe_fee"), ZERO, output_field=MONEY),
        refunds=Coalesce(Sum("refunded_amount"), ZERO, output_field=MONEY),
        discounts=Coalesce(Sum("discount_total"), ZERO, output_field=MONEY),
        orders=Count("id"),
        refunded_orders=Count("id", filter=Q(status=Order.Status.REFUNDED)),
        disputed_orders=Count("id", filter=Q(status=Order.Status.DISPUTED)),
    )
    agg["units"] = sale_items(period).aggregate(n=Coalesce(Sum("quantity"), 0))["n"]
    agg["net"] = agg["revenue"] - agg["fees"] - agg["refunds"]
    agg["aov"] = (agg["revenue"] / agg["orders"]).quantize(Decimal("0.01")) if agg["orders"] else ZERO
    return agg


def pct_change(current, previous):
    if not previous:
        return None if not current else 100.0
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def kpis(period):
    now, before = totals(period), totals(period.previous)
    keys = ["revenue", "net", "orders", "units", "aov"]
    return now, {k: pct_change(now[k], before[k]) for k in keys}


# --- time series ------------------------------------------------------------------

TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}


def _buckets(period):
    """All bucket start dates in the period so charts show zero-sale days too."""
    start = period.start_date
    end = period.end_date
    out = []
    if period.grain == "day":
        d = start
        while d <= end:
            out.append(d)
            d += timedelta(days=1)
    elif period.grain == "week":
        d = start - timedelta(days=start.weekday())
        while d <= end:
            out.append(d)
            d += timedelta(weeks=1)
    else:
        d = start.replace(day=1)
        while d <= end:
            out.append(d)
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def series(period):
    """{'labels': [...], 'revenue': [...], 'units': [...], 'orders': [...]} bucketed by the period grain."""
    trunc = TRUNC[period.grain]
    tz = timezone.get_current_timezone()
    rev = {
        r["b"].date() if hasattr(r["b"], "date") else r["b"]: r
        for r in sales(period).annotate(b=trunc("paid_at", tzinfo=tz)).values("b")
        .annotate(revenue=Sum("total"), orders=Count("id"))
    }
    units = {
        r["b"].date() if hasattr(r["b"], "date") else r["b"]: r["units"]
        for r in sale_items(period).annotate(b=trunc("order__paid_at", tzinfo=tz)).values("b")
        .annotate(units=Sum("quantity"))
    }
    fmt = {"day": "%b %d", "week": "Wk %b %d", "month": "%b %Y"}[period.grain]
    labels, revenue, orders, unit_counts = [], [], [], []
    for b in _buckets(period):
        labels.append(b.strftime(fmt))
        revenue.append(float(rev.get(b, {}).get("revenue") or 0))
        orders.append(rev.get(b, {}).get("orders") or 0)
        unit_counts.append(units.get(b, 0) or 0)
    return {"labels": labels, "revenue": revenue, "orders": orders, "units": unit_counts}


# --- breakdowns --------------------------------------------------------------------

def top_products(period, order_by="revenue", limit=10):
    return list(
        sale_items(period).values("product_id", "product__title")
        .annotate(units=Sum("quantity"), revenue=Sum("revenue"))
        .order_by(f"-{order_by}")[:limit]
    )


def by_category(period):
    return list(
        sale_items(period).values("product__category__name")
        .annotate(units=Sum("quantity"), revenue=Sum("revenue")).order_by("-revenue")
    )


def by_framework(period):
    return list(
        sale_items(period).filter(product__frameworks__isnull=False).values("product__frameworks__name")
        .annotate(units=Sum("quantity"), revenue=Sum("revenue")).order_by("-revenue")
    )


def by_license(period):
    return list(
        sale_items(period).values("license_tier").annotate(units=Sum("quantity"), revenue=Sum("revenue"))
        .order_by("-revenue")
    )


def by_country(period):
    return list(
        sales(period).values("country").annotate(orders=Count("id"), revenue=Sum("total")).order_by("-revenue")
    )


def by_source(period):
    return list(
        sales(period).values("utm_source")
        .annotate(orders=Count("id"), revenue=Sum("total")).order_by("-revenue")
    )


def by_coupon(period):
    return list(
        sales(period).exclude(coupon_code="").values("coupon_code")
        .annotate(orders=Count("id"), revenue=Sum("total"), discount=Sum("discount_total")).order_by("-orders")
    )


def customer_mix(period):
    """New vs returning: a customer is 'new' if their first sale ever falls inside the period."""
    emails = sales(period).exclude(email="").values_list("email", flat=True).distinct()
    first = (
        Order.objects.filter(status__in=SALE_STATUSES, email__in=emails)
        .values("email").annotate(first=Min("paid_at"))
    )
    new = sum(1 for r in first if r["first"] >= period.start)
    total = len(set(e.lower() for e in emails))
    return {"new": new, "returning": max(total - new, 0), "total": total}


def funnel(period):
    """Checkout funnel we can measure ourselves: checkouts started → paid."""
    started = Order.objects.filter(created_at__gte=period.start, created_at__lt=period.end).count()
    paid = sales(period).count()
    return {"started": started, "paid": paid, "rate": round(paid / started * 100, 1) if started else None}


def recent_orders(limit=10):
    return Order.objects.exclude(status=Order.Status.PENDING).order_by("-created_at")[:limit]
