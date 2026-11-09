import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_admins
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import cents
from apps.core.middleware import ATTRIBUTION_SESSION_KEY
from apps.core.models import SiteSettings
from apps.orders.cart import Cart
from apps.orders.models import Order
from apps.orders.services import create_order_from_cart, mark_order_paid

from .forms import CheckoutForm
from .models import StripeEvent
from .stripe_client import get_client

logger = logging.getLogger(__name__)


MIN_CHARGE = Decimal("0.50")


def _attribution(request):
    return request.session.get(ATTRIBUTION_SESSION_KEY) or {}


@require_POST
def checkout(request):
    """Validate the cart + buyer details, create a pending Order, and redirect to Stripe Checkout."""
    cart = Cart(request)
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return _back_to_cart(request, cart, form)

    email, name = form.cleaned_data["email"].lower(), form.cleaned_data["name"]
    cart.lines(email=email)  # re-validates the coupon for this customer
    if cart.coupon_error:
        messages.error(request, cart.coupon_error)
        cart.set_coupon("")
        return _back_to_cart(request, cart, form)
    if not len(cart.lines(email=email)):
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")

    order = create_order_from_cart(cart, email=email, name=name, user=request.user, attribution=_attribution(request))

    if order.total == 0:  # 100% coupon: nothing to charge
        mark_order_paid(order)
        cart.clear()
        return redirect(reverse("payments:success") + f"?order={order.number}")
    if order.total < MIN_CHARGE:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
        messages.error(request, f"The order total must be at least ${MIN_CHARGE} after discounts.")
        return redirect("orders:cart")

    try:
        session = get_client().v1.checkout.sessions.create(params=_session_params(order))
    except (stripe.StripeError, ImproperlyConfigured):
        logger.exception("Stripe checkout session creation failed for order %s", order.number)
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        messages.error(request, "We couldn't start checkout. Please try again in a moment.")
        return redirect("orders:cart")

    order.stripe_checkout_session_id = session.id
    order.save(update_fields=["stripe_checkout_session_id"])
    return redirect(session.url, permanent=False)


def _back_to_cart(request, cart, form):
    from apps.orders.views import _cart_context

    return render(request, "orders/cart.html", _cart_context(request, cart, form=form), status=400)


def _session_params(order):
    items = list(order.items.select_related("product"))
    params = {
        "mode": "payment",
        "line_items": [
            {
                "quantity": item.quantity,
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": cents(item.unit_price),
                    "product_data": {
                        "name": f"{item.product_title} – {item.license_label} license",
                        "description": item.product.short_description[:300],
                    },
                },
            }
            for item in items
        ],
        "customer_email": order.email,
        "client_reference_id": str(order.number),
        "metadata": {"order_number": str(order.number)},
        "payment_intent_data": {"metadata": {"order_number": str(order.number)}},
        "success_url": settings.SITE_URL + reverse("payments:success") + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": settings.SITE_URL + reverse("payments:cancel") + f"?order={order.number}",
    }
    if order.discount_total > 0:
        # Our coupon rules decide the discount; a one-off Stripe coupon just displays and applies it.
        stripe_coupon = get_client().v1.coupons.create(
            params={
                "amount_off": cents(order.discount_total),
                "currency": order.currency,
                "duration": "once",
                "max_redemptions": 1,
                "name": order.coupon_code or "Discount",
            }
        )
        params["discounts"] = [{"coupon": stripe_coupon.id}]
    if SiteSettings.load().stripe_invoices:
        params["invoice_creation"] = {
            "enabled": True,
            "invoice_data": {
                "metadata": {"order_number": str(order.number)},
                "footer": f"{settings.SITE_NAME} · Order {order.short_number}",
            },
        }
    return params


@require_GET
def checkout_success(request):
    """Shown after Stripe redirects back. Fulfilment happens in the webhook, not here."""
    qs = Order.objects.prefetch_related("items__entitlements__product")
    order = None
    if session_id := request.GET.get("session_id"):
        order = qs.filter(stripe_checkout_session_id=session_id).first()
    elif number := request.GET.get("order"):
        try:
            order = qs.filter(number=number).first()
        except ValidationError:
            order = None
    if order is not None:
        Cart(request).clear()
    return render(request, "payments/success.html", {"order": order})


@require_GET
def checkout_cancel(request):
    if number := request.GET.get("order"):
        Order.objects.filter(number=number, status=Order.Status.PENDING).update(status=Order.Status.CANCELLED)
    return render(request, "payments/cancel.html")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Rejected Stripe webhook with invalid payload/signature")
        return HttpResponseBadRequest("invalid")

    try:
        with transaction.atomic():
            StripeEvent.objects.create(event_id=event["id"], type=event["type"], payload=event.to_dict())
            _handle_event(event)
    except IntegrityError:
        # Already processed (Stripe retried). Acknowledge so it stops retrying.
        return HttpResponse(status=200)

    return HttpResponse(status=200)


def _handle_event(event):
    obj = event["data"]["object"]
    etype = event["type"]

    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") not in ("paid", "no_payment_required"):
            return  # async methods: wait for async_payment_succeeded
        order = _order_for_session(obj)
        if order:
            details = obj.get("customer_details") or {}
            payment_intent_id = obj.get("payment_intent") or ""
            mark_order_paid(
                order,
                email=(details.get("email") or "").lower(),
                name=details.get("name") or "",
                country=((details.get("address") or {}).get("country") or ""),
                payment_intent_id=payment_intent_id,
                stripe_fee=_stripe_fee(payment_intent_id),
                invoice_url=_invoice_pdf(obj.get("invoice")),
            )

    elif etype in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        order = _order_for_session(obj)
        if order and order.status == Order.Status.PENDING:
            order.status = Order.Status.FAILED if etype.endswith("failed") else Order.Status.CANCELLED
            order.save(update_fields=["status"])

    elif etype == "charge.refunded":
        order = _order_for_payment_intent(obj.get("payment_intent"))
        if order:
            order.refunded_amount = Decimal(obj.get("amount_refunded", 0)) / 100
            if obj.get("refunded"):  # fully refunded → downloads stop working
                order.status = Order.Status.REFUNDED
            order.save(update_fields=["refunded_amount", "status"])

    elif etype == "charge.dispute.created":
        order = _order_for_payment_intent(obj.get("payment_intent"))
        if order and order.status == Order.Status.PAID:
            order.status = Order.Status.DISPUTED
            order.save(update_fields=["status"])
            mail_admins(
                f"Dispute opened on order {order.short_number}",
                f"Reason: {obj.get('reason')}\nAmount: {obj.get('amount', 0) / 100} {order.currency.upper()}\n"
                f"Respond in the Stripe Dashboard before the deadline.",
                fail_silently=True,
            )

    elif etype == "charge.dispute.closed":
        order = _order_for_payment_intent(obj.get("payment_intent"))
        if order and order.status == Order.Status.DISPUTED:
            # Won: restore access. Lost: the money was returned to the buyer.
            order.status = Order.Status.PAID if obj.get("status") == "won" else Order.Status.REFUNDED
            if order.status == Order.Status.REFUNDED:
                order.refunded_amount = order.total
            order.save(update_fields=["status", "refunded_amount"])


def _order_for_session(session):
    number = (session.get("metadata") or {}).get("order_number") or session.get("client_reference_id")
    order = Order.objects.filter(number=number).first() if number else None
    if order is None:
        order = Order.objects.filter(stripe_checkout_session_id=session.get("id")).first()
    if order is None:
        logger.error("Stripe session %s has no matching order", session.get("id"))
    return order


def _order_for_payment_intent(payment_intent_id):
    if not payment_intent_id:
        return None
    order = Order.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    if order is None:
        logger.warning("No order for payment intent %s", payment_intent_id)
    return order


def _stripe_fee(payment_intent_id):
    """Stripe's processing fee for reports. Best effort: never blocks fulfilment."""
    if not payment_intent_id:
        return None
    try:
        pi = get_client().v1.payment_intents.retrieve(
            payment_intent_id, params={"expand": ["latest_charge.balance_transaction"]}
        )
        bt = pi.latest_charge.balance_transaction
        return Decimal(bt.fee) / 100
    except Exception:
        logger.warning("Couldn't fetch Stripe fee for %s", payment_intent_id, exc_info=True)
        return None


def _invoice_pdf(invoice_id):
    if not invoice_id:
        return ""
    try:
        invoice = get_client().v1.invoices.retrieve(invoice_id)
        return invoice.invoice_pdf or invoice.hosted_invoice_url or ""
    except Exception:
        logger.warning("Couldn't fetch Stripe invoice %s", invoice_id, exc_info=True)
        return ""
