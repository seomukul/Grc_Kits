from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Order


@login_required
def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items__entitlements"), number=number, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
