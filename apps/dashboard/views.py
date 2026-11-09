from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.downloads.models import Entitlement
from apps.orders.models import Order


@login_required
def home(request):
    orders = Order.objects.filter(user=request.user).exclude(status=Order.Status.PENDING).prefetch_related("items")
    entitlements = (
        Entitlement.objects.filter(order_item__order__user=request.user, order_item__order__status=Order.Status.PAID)
        .select_related("product", "order_item__order")
        .order_by("-created_at")
    )
    return render(request, "dashboard/home.html", {"orders": orders[:20], "entitlements": entitlements})
