from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.models import Order

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def submit_review(request, slug):
    """HTMX endpoint: returns the form partial (with errors) or a thank-you partial."""
    product = get_object_or_404(Product.objects.published(), slug=slug)
    if Review.objects.filter(product=product, user=request.user).exists():
        return render(request, "reviews/_thanks.html", {"already": True})

    form = ReviewForm(request.POST)
    if not form.is_valid():
        return render(request, "reviews/_form.html", {"form": form, "product": product})

    review = form.save(commit=False)
    review.product = product
    review.user = request.user
    review.is_verified_purchase = Order.objects.filter(
        user=request.user, status=Order.Status.PAID, items__product=product
    ).exists()
    review.save()
    return render(request, "reviews/_thanks.html", {"review": review})
