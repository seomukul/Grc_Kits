"""Unfold DASHBOARD_CALLBACK: turns the admin home page into the sales dashboard."""

import json
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html

from apps.catalog.models import LicenseTier

from . import analytics

GOLD = "#c29b4c"
NAVY = "#0e1622"


def _money(v):
    return f"${float(v or 0):,.2f}"


def _change(v):
    if v is None:
        return None
    return {"value": f"{'+' if v >= 0 else ''}{v}%", "up": v >= 0}


def _table(headers, rows):
    return {"headers": headers, "rows": rows}


def dashboard_callback(request, context):
    if not request.user.has_perm("orders.view_order"):
        return context  # editors etc. just see the app list

    period = analytics.resolve_period(request.GET)
    now, change = analytics.kpis(period)
    ser = analytics.series(period)
    qs = urlencode({"period": period.key, "start": period.start_date, "end": period.end_date})

    def export(report):
        return reverse("dashboard:export", args=[report]) + "?" + qs

    kpi_cards = [
        {"title": "Revenue", "value": _money(now["revenue"]), "change": _change(change["revenue"]), "icon": "payments"},
        {"title": "Net revenue", "value": _money(now["net"]), "change": _change(change["net"]), "icon": "account_balance",
         "note": f"after {_money(now['fees'])} fees & {_money(now['refunds'])} refunds"},
        {"title": "Orders", "value": now["orders"], "change": _change(change["orders"]), "icon": "receipt_long"},
        {"title": "Units sold", "value": now["units"], "change": _change(change["units"]), "icon": "inventory_2"},
        {"title": "Avg. order value", "value": _money(now["aov"]), "change": _change(change["aov"]), "icon": "query_stats"},
    ]

    revenue_chart = json.dumps({
        "labels": ser["labels"],
        "datasets": [{"label": "Revenue (USD)", "data": ser["revenue"], "backgroundColor": GOLD, "borderColor": GOLD}],
    })
    units_chart = json.dumps({
        "labels": ser["labels"],
        "datasets": [
            {"label": "Units", "data": ser["units"], "backgroundColor": NAVY, "borderColor": NAVY},
            {"label": "Orders", "data": ser["orders"], "backgroundColor": GOLD, "borderColor": GOLD},
        ],
    })

    tiers = dict(LicenseTier.choices)
    mix = analytics.customer_mix(period)
    mix["new_pct"] = round(mix["new"] / mix["total"] * 100) if mix["total"] else 0
    funnel = analytics.funnel(period)

    context.update({
        "analytics": True,
        "period": period,
        "presets": analytics.PRESETS.items(),
        "kpi_cards": kpi_cards,
        "revenue_chart": revenue_chart,
        "units_chart": units_chart,
        "totals": now,
        "mix": mix,
        "funnel": funnel,
        "export_links": {r: export(r) for r in ("orders", "products", "countries", "sources", "summary")},
        "tables": [
            ("Top products by revenue", export("products"), _table(
                ["Product", "Units", "Revenue"],
                [[r["product__title"], r["units"], _money(r["revenue"])] for r in analytics.top_products(period)])),
            ("Top products by units", export("products"), _table(
                ["Product", "Units", "Revenue"],
                [[r["product__title"], r["units"], _money(r["revenue"])] for r in analytics.top_products(period, "units")])),
            ("Sales by discipline", None, _table(
                ["Discipline", "Units", "Revenue"],
                [[r["product__category__name"], r["units"], _money(r["revenue"])] for r in analytics.by_category(period)])),
            ("Sales by framework", None, _table(
                ["Framework", "Units", "Revenue"],
                [[r["product__frameworks__name"], r["units"], _money(r["revenue"])] for r in analytics.by_framework(period)])),
            ("Sales by country", export("countries"), _table(
                ["Country", "Orders", "Revenue"],
                [[r["country"] or "Unknown", r["orders"], _money(r["revenue"])] for r in analytics.by_country(period)])),
            ("Traffic source", export("sources"), _table(
                ["Source", "Orders", "Revenue"],
                [[r["utm_source"] or "Direct / unknown", r["orders"], _money(r["revenue"])] for r in analytics.by_source(period)])),
            ("License tiers", None, _table(
                ["License", "Units", "Revenue"],
                [[tiers.get(r["license_tier"], r["license_tier"]), r["units"], _money(r["revenue"])] for r in analytics.by_license(period)])),
            ("Coupons", None, _table(
                ["Code", "Orders", "Discount given"],
                [[r["coupon_code"], r["orders"], _money(r["discount"])] for r in analytics.by_coupon(period)])),
        ],
        "recent": _table(
            ["Order", "Customer", "Status", "Total", "Date"],
            [[
                format_html('<a class="text-primary-600 underline" href="{}">{}</a>',
                            reverse("admin:orders_order_change", args=[o.pk]), o.short_number),
                o.email or "–", o.get_status_display(), _money(o.total), o.created_at.strftime("%b %d, %H:%M"),
            ] for o in analytics.recent_orders()],
        ),
    })
    return context
