from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.downloads.models import Entitlement
from apps.orders.models import Order

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def submit_review(request, slug):
    """HTMX endpoint: returns the form partial (with errors) or a thank-you partial."""
    product = get_object_or_404(Product.objects.purchasable(), slug=slug)
    is_buyer = Entitlement.objects.filter(
        order_item__order__user=request.user, order_item__order__status=Order.Status.PAID, product=product
    ).exists()
    if not is_buyer:
        return HttpResponseForbidden("Only verified buyers can review this product.")
    if Review.objects.filter(product=product, user=request.user).exists():
        return render(request, "reviews/_thanks.html", {"already": True})

    form = ReviewForm(request.POST)
    if not form.is_valid():
        return render(request, "reviews/_form.html", {"review_form": form, "product": product})

    review = form.save(commit=False)
    review.product = product
    review.user = request.user
    review.is_verified_purchase = True
    review.save()
    return render(request, "reviews/_thanks.html", {"review": review})
