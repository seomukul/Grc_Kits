from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ("email", "source", "is_active", "created_at")
    list_filter = ("is_active", "source")
    search_fields = ("email",)


from unfold.decorators import display  # noqa: E402

from .models import Coupon  # noqa: E402


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ("code", "label", "scope", "uses", "max_uses", "valid_until", "is_active")
    list_filter = ("is_active", "discount_type")
    list_editable = ("is_active",)
    search_fields = ("code", "description")
    filter_horizontal = ("products",)
    fieldsets = (
        (None, {"fields": ("code", "description", "is_active")}),
        ("Discount", {"fields": ("discount_type", "value", "min_order_amount")}),
        ("Applies to", {"fields": ("products",), "description": "Leave empty for every product (sitewide)."}),
        ("Limits", {"fields": ("valid_from", "valid_until", "max_uses", "max_uses_per_customer")}),
    )

    @display(description="Scope")
    def scope(self, obj):
        n = obj.products.count()
        return "Sitewide" if not n else f"{n} product(s)"

    @display(description="Used")
    def uses(self, obj):
        return obj.times_used()
