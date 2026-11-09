import logging

import stripe
from django.contrib import admin, messages
from django.db import transaction
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.payments.stripe_client import get_client

from .emails import send_order_confirmation
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "product_title", "license_tier", "unit_price", "discount")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        "short_number", "email", "show_status", "total", "discount_total", "coupon_code", "country", "paid_at",
    )
    list_filter = ("status", "country", "utm_source", "created_at")
    search_fields = ("number", "email", "name", "coupon_code", "stripe_checkout_session_id", "stripe_payment_intent_id")
    readonly_fields = (
        "number", "subtotal", "discount_total", "total", "stripe_fee", "refunded_amount", "net",
        "coupon", "coupon_code", "stripe_checkout_session_id", "stripe_payment_intent_id", "invoice_url",
        "paid_at", "created_at", "utm_source", "utm_medium", "utm_campaign", "referrer",
    )
    fieldsets = (
        (None, {"fields": ("number", "status", "user", "email", "name", "country")}),
        ("Money", {"fields": ("subtotal", "discount_total", "total", "stripe_fee", "refunded_amount", "net", "coupon", "coupon_code")}),
        ("Stripe", {"fields": ("stripe_checkout_session_id", "stripe_payment_intent_id", "invoice_url", "paid_at", "created_at")}),
        ("Traffic source", {"classes": ("collapse",), "fields": ("utm_source", "utm_medium", "utm_campaign", "referrer")}),
    )
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    actions = ["resend_email", "refund"]
    actions_detail = ["resend_email_detail", "refund_detail"]

    @display(
        description="Status",
        label={
            "paid": "success", "pending": "warning", "failed": "danger", "refunded": "info",
            "disputed": "danger", "cancelled": "info",
        },
    )
    def show_status(self, obj):
        return obj.status

    @display(description="Net revenue")
    def net(self, obj):
        return f"${obj.net_revenue}"

    # --- actions ------------------------------------------------------------
    def _resend(self, request, orders):
        sent = 0
        for order in orders:
            if order.status == Order.Status.PAID and order.email:
                send_order_confirmation(order)
                sent += 1
        messages.success(request, f"Resent the receipt + download links for {sent} order(s).")

    def _refund(self, request, orders):
        client = get_client()
        for order in orders:
            if order.status not in (Order.Status.PAID, Order.Status.DISPUTED):
                messages.warning(request, f"{order}: only paid orders can be refunded.")
                continue
            if order.stripe_payment_intent_id:
                try:
                    client.v1.refunds.create(params={"payment_intent": order.stripe_payment_intent_id})
                except stripe.StripeError as exc:
                    logger.exception("Refund failed for %s", order)
                    messages.error(request, f"{order}: Stripe refused the refund ({exc.user_message or exc}).")
                    continue
            with transaction.atomic():
                order.status = Order.Status.REFUNDED
                order.refunded_amount = order.total
                order.save(update_fields=["status", "refunded_amount"])
            messages.success(request, f"{order} refunded. Downloads are now disabled.")

    @action(description="Resend receipt + download links")
    def resend_email(self, request, queryset):
        self._resend(request, queryset)

    @action(description="Refund in Stripe and disable downloads")
    def refund(self, request, queryset):
        self._refund(request, queryset)

    @action(description="Resend receipt + download links")
    def resend_email_detail(self, request, object_id):
        from django.shortcuts import redirect

        self._resend(request, Order.objects.filter(pk=object_id))
        return redirect("admin:orders_order_change", object_id)

    @action(description="Refund in Stripe")
    def refund_detail(self, request, object_id):
        from django.shortcuts import redirect

        self._refund(request, Order.objects.filter(pk=object_id))
        return redirect("admin:orders_order_change", object_id)
