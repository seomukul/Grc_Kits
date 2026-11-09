from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ("email", "source", "is_active", "created_at", "esp_synced_at", "esp_error")
    list_filter = ("is_active", "source", ("esp_synced_at", admin.EmptyFieldListFilter))
    search_fields = ("email",)
    readonly_fields = ("consent_ip", "unsubscribed_at", "esp_synced_at", "esp_error", "created_at")
    actions = ["sync_to_esp", "export_csv"]

    @action(description="Sync selected to email tool")
    def sync_to_esp(self, request, queryset):
        from django.contrib import messages

        from . import esp

        if not esp.enabled():
            messages.warning(request, "No email tool configured (set ESP_PROVIDER and ESP_API_KEY).")
            return
        ok = sum(esp.sync(s) for s in queryset)
        messages.success(request, f"Synced {ok} of {queryset.count()} subscriber(s).")

    @action(description="Export selected to CSV")
    def export_csv(self, request, queryset):
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="grckits-subscribers.csv"'
        response.write("\ufeff")
        w = csv.writer(response)
        w.writerow(["Email", "Source", "Active", "Subscribed at", "Unsubscribed at"])
        for s in queryset:
            w.writerow([s.email, s.source, s.is_active, s.created_at, s.unsubscribed_at])
        return response


from unfold.decorators import action, display  # noqa: E402

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
