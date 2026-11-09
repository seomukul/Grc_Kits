import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import Product
from apps.orders.models import Order
from apps.orders.services import create_order_for_product, mark_order_paid

from .models import StripeEvent
from .stripe_client import get_client

logger = logging.getLogger(__name__)


@require_POST
def create_checkout_session(request, slug):
    """Create a pending Order and redirect the buyer to Stripe-hosted Checkout."""
    product = get_object_or_404(Product.objects.published(), slug=slug)
    order = create_order_for_product(product, user=request.user)

    params = {
        "mode": "payment",
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": product.currency,
                    "unit_amount": product.price_cents,
                    "product_data": {"name": product.title, "description": product.short_description[:300]},
                },
            }
        ],
        "client_reference_id": str(order.number),
        "metadata": {"order_number": str(order.number)},
        "success_url": settings.SITE_URL + reverse("payments:success") + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": settings.SITE_URL + reverse("payments:cancel") + f"?order={order.number}",
        "allow_promotion_codes": True,
    }
    if order.email:
        params["customer_email"] = order.email
    else:
        params["customer_creation"] = "always"

    try:
        session = get_client().v1.checkout.sessions.create(params=params)
    except stripe.StripeError:
        logger.exception("Stripe checkout session creation failed for order %s", order.number)
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        messages.error(request, "We couldn't start checkout. Please try again in a moment.")
        return redirect(product.get_absolute_url())

    order.stripe_checkout_session_id = session.id
    order.save(update_fields=["stripe_checkout_session_id"])

    if request.htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = session.url
        return response
    return redirect(session.url, permanent=False)


@require_GET
def checkout_success(request):
    """Shown after Stripe redirects back. Fulfilment happens in the webhook, not here."""
    order = None
    if session_id := request.GET.get("session_id"):
        order = Order.objects.filter(stripe_checkout_session_id=session_id).prefetch_related("items").first()
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
        if obj.get("payment_status") != "paid":
            return  # async methods: wait for async_payment_succeeded
        order = _order_for_session(obj)
        if order:
            details = obj.get("customer_details") or {}
            mark_order_paid(order, email=details.get("email") or "", payment_intent_id=obj.get("payment_intent") or "")

    elif etype in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        order = _order_for_session(obj)
        if order and order.status == Order.Status.PENDING:
            order.status = Order.Status.FAILED if etype.endswith("failed") else Order.Status.CANCELLED
            order.save(update_fields=["status"])

    elif etype == "charge.refunded":
        if pi := obj.get("payment_intent"):
            Order.objects.filter(stripe_payment_intent_id=pi).update(status=Order.Status.REFUNDED)


def _order_for_session(session):
    number = (session.get("metadata") or {}).get("order_number") or session.get("client_reference_id")
    order = Order.objects.filter(number=number).first() if number else None
    if order is None:
        order = Order.objects.filter(stripe_checkout_session_id=session.get("id")).first()
    if order is None:
        logger.error("Stripe session %s has no matching order", session.get("id"))
    return order
