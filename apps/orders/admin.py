from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_title", "unit_price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ("short_number", "email", "user", "show_status", "total", "currency", "created_at", "paid_at")
    list_filter = ("status", "created_at")
    search_fields = ("number", "email", "stripe_checkout_session_id", "stripe_payment_intent_id")
    readonly_fields = ("number", "stripe_checkout_session_id", "stripe_payment_intent_id", "paid_at", "created_at")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"

    @display(
        description="Status",
        label={"paid": "success", "pending": "warning", "failed": "danger", "refunded": "info", "cancelled": "info"},
    )
    def show_status(self, obj):
        return obj.status
