"""CSV exports for the sales dashboard (open directly in Excel)."""

import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse

from apps.catalog.models import LicenseTier

from . import analytics


def _csv(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM so Excel opens UTF-8 correctly
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


def _orders(period):
    tiers = dict(LicenseTier.choices)
    rows = []
    for o in analytics.sales(period).prefetch_related("items").order_by("paid_at"):
        rows.append([
            o.short_number, o.paid_at.strftime("%Y-%m-%d %H:%M"), o.get_status_display(), o.email, o.name, o.country,
            "; ".join(f"{i.product_title} ({tiers.get(i.license_tier, i.license_tier)})" for i in o.items.all()),
            o.subtotal, o.discount_total, o.coupon_code, o.total, o.stripe_fee, o.refunded_amount, o.net_revenue,
            o.utm_source, o.utm_medium, o.utm_campaign, o.referrer,
        ])
    header = ["Order", "Paid at", "Status", "Email", "Name", "Country", "Items", "Subtotal", "Discount", "Coupon",
              "Total", "Stripe fee", "Refunded", "Net", "UTM source", "UTM medium", "UTM campaign", "Referrer"]
    return header, rows


def _products(period):
    return ["Product", "Units", "Revenue"], [
        [r["product__title"], r["units"], r["revenue"]] for r in analytics.top_products(period, limit=None)
    ]


def _countries(period):
    return ["Country", "Orders", "Revenue"], [[r["country"] or "Unknown", r["orders"], r["revenue"]] for r in analytics.by_country(period)]


def _sources(period):
    return ["Source", "Orders", "Revenue"], [[r["utm_source"] or "Direct / unknown", r["orders"], r["revenue"]] for r in analytics.by_source(period)]


def _summary(period):
    t = analytics.totals(period)
    rows = [[label, t[key]] for key, label in [
        ("revenue", "Revenue"), ("discounts", "Discounts"), ("fees", "Stripe fees"), ("refunds", "Refunds"),
        ("net", "Net revenue"), ("orders", "Orders"), ("units", "Units sold"), ("aov", "Average order value"),
        ("refunded_orders", "Fully refunded orders"), ("disputed_orders", "Disputed orders"),
    ]]
    ser = analytics.series(period)
    rows += [[], ["Period", "Revenue", "Orders", "Units"]]
    rows += [list(r) for r in zip(ser["labels"], ser["revenue"], ser["orders"], ser["units"])]
    return [f"{period.label}", f"{period.start_date} to {period.end_date}"], rows


REPORTS = {"orders": _orders, "products": _products, "countries": _countries, "sources": _sources, "summary": _summary}


@staff_member_required
def export(request, report):
    if report not in REPORTS:
        raise Http404
    if not request.user.has_perm("orders.view_order"):
        raise PermissionDenied
    period = analytics.resolve_period(request.GET)
    header, rows = REPORTS[report](period)
    return _csv(f"grckits-{report}-{period.start_date}-{period.end_date}.csv", header, rows)
