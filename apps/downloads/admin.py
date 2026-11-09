from django.conf import settings
from django.contrib import admin, messages
from django.template.defaultfilters import filesizeformat
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .forms import ProductFileVersionForm
from .models import DownloadLog, Entitlement, ProductFile, ProductFileVersion
from .notifications import notify_buyers_of_update


class ProductFileVersionInline(TabularInline):
    model = ProductFileVersion
    form = ProductFileVersionForm
    extra = 1
    fields = ("version", "file", "uploaded_key", "changelog", "human_size", "created_at")
    readonly_fields = ("human_size", "created_at")
    ordering = ("-created_at",)

    def get_fields(self, request, obj=None):
        upload_field = "uploaded_key" if settings.USE_R2 else "file"
        return ["version", upload_field, "changelog", "human_size", "created_at"]

    @display(description="Size")
    def human_size(self, obj):
        return filesizeformat(obj.size) if obj.size else "–"


@admin.register(ProductFile)
class ProductFileAdmin(ModelAdmin):
    list_display = ("title", "product", "latest", "is_active", "updated_at")
    list_filter = ("is_active", "product")
    search_fields = ("title", "product__title")
    autocomplete_fields = ("product",)
    inlines = [ProductFileVersionInline]
    actions = ["notify_buyers"]
    actions_detail = ["notify_buyers_detail"]

    @display(description="Latest version")
    def latest(self, obj):
        v = obj.latest_version
        return f"v{v.version}" if v else "–"

    @action(description="Email buyers: new version available")
    def notify_buyers(self, request, queryset):
        total = sum(notify_buyers_of_update(pf) for pf in queryset)
        messages.success(request, f"Sent {total} update email(s).")

    @action(description="Email buyers about latest version")
    def notify_buyers_detail(self, request, object_id):
        from django.shortcuts import redirect

        sent = notify_buyers_of_update(ProductFile.objects.get(pk=object_id))
        messages.success(request, f"Sent {sent} update email(s).")
        return redirect("admin:downloads_productfile_change", object_id)


@admin.register(Entitlement)
class EntitlementAdmin(ModelAdmin):
    list_display = ("product", "order_item", "max_downloads", "revoked", "created_at")
    list_filter = ("revoked",)
    search_fields = ("token", "order_item__order__email", "product__title")
    readonly_fields = ("token", "order_item", "product", "created_at")
    list_editable = ("revoked",)


@admin.register(DownloadLog)
class DownloadLogAdmin(ModelAdmin):
    list_display = ("created_at", "entitlement", "product_file", "version", "ip_address")
    search_fields = ("entitlement__order_item__order__email", "ip_address")
    readonly_fields = [f.name for f in DownloadLog._meta.fields]

    def has_add_permission(self, request):
        return False
