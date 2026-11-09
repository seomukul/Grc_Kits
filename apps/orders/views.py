from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import LicenseTier, Product
from apps.payments.forms import CheckoutForm

from .cart import Cart
from .models import Order, OrderItem


@login_required
def order_detail(request, number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__entitlements__product"), number=number, user=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})


def _also_bought(cart, limit=3):
    """'Customers also bought': products most often in the same paid orders as the cart items."""
    ids = cart.product_ids()
    if not ids:
        return Product.objects.none()
    order_ids = OrderItem.objects.filter(product_id__in=ids, order__status="paid").values("order_id")
    popular = (
        OrderItem.objects.filter(order_id__in=order_ids)
        .exclude(product_id__in=ids)
        .values("product_id")
        .annotate(n=Count("id"))
        .order_by("-n")
        .values_list("product_id", flat=True)[:limit]
    )
    products = list(Product.objects.listed().filter(pk__in=list(popular)).select_related("category"))
    if len(products) < limit:  # fall back to featured products
        products += list(
            Product.objects.listed().filter(is_featured=True).exclude(pk__in=ids + [p.pk for p in products])
            .select_related("category")[: limit - len(products)]
        )
    return products


def _cart_context(request, cart, form=None):
    email = request.user.email if request.user.is_authenticated else None
    lines = cart.lines(email=email)
    return {
        "cart": cart,
        "lines": lines,
        "totals": cart.totals(email=email),
        "form": form or CheckoutForm(initial={
            "email": email or "",
            "name": request.user.get_full_name() if request.user.is_authenticated else "",
        }),
        "also_bought": _also_bought(cart),
    }


@require_GET
def cart_detail(request):
    return render(request, "orders/cart.html", _cart_context(request, Cart(request)))


def _cart_changed(request, cart, message=""):
    """HTMX: re-render the cart body and tell the header badge to refresh."""
    if request.htmx:
        response = render(request, "orders/_cart_body.html", _cart_context(request, cart))
        response["HX-Trigger"] = '{"cartChanged": {"count": %d}}' % len(cart)
        return response
    if message:
        messages.success(request, message)
    return redirect("orders:cart")


@require_POST
def cart_add(request, slug):
    product = get_object_or_404(Product.objects.purchasable(), slug=slug)
    cart = Cart(request)
    try:
        cart.add(product, request.POST.get("license", LicenseTier.SINGLE))
    except ValueError:
        messages.error(request, "Please choose a valid license.")
        return redirect(product.get_absolute_url())
    if request.htmx:
        response = HttpResponse(status=204)
        response["HX-Trigger"] = '{"cartChanged": {"count": %d}}' % len(cart)
        response["HX-Redirect"] = request.build_absolute_uri("/cart/")
        return response
    return redirect("orders:cart")


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return _cart_changed(request, cart, "Removed from cart.")


@require_POST
def cart_coupon(request):
    cart = Cart(request)
    if "remove" in request.POST:
        cart.set_coupon("")
    else:
        cart.set_coupon(request.POST.get("code", ""))
        cart.lines()  # validate now so we can show the error
        if cart.coupon_error:
            error = cart.coupon_error
            cart.set_coupon("")
            if request.htmx:
                ctx = _cart_context(request, cart)
                ctx["coupon_error"] = error
                return render(request, "orders/_cart_body.html", ctx)
            messages.error(request, error)
            return redirect("orders:cart")
    return _cart_changed(request, cart, "Coupon updated.")


@require_GET
def cart_restore(request, token):
    """Link from the abandoned-checkout email: refill the cart from that order."""
    from django.core import signing

    from .abandoned import SALT

    try:
        number = signing.loads(token, salt=SALT, max_age=60 * 60 * 24 * 14)
    except signing.BadSignature:
        messages.error(request, "That link has expired. Your items may still be available in the shop.")
        return redirect("catalog:list")
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), number=number)
    cart = Cart(request)
    for item in order.items.all():
        try:
            cart.add(item.product, item.license_tier)
        except ValueError:
            continue
    if order.coupon_code:
        cart.set_coupon(order.coupon_code)
    return redirect("orders:cart")
