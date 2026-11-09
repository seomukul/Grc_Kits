from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Entitlement, ProductFile


@admin.register(ProductFile)
class ProductFileAdmin(ModelAdmin):
    list_display = ("title", "product", "version", "is_active", "updated_at")
    list_filter = ("is_active", "product")
    search_fields = ("title", "product__title")


@admin.register(Entitlement)
class EntitlementAdmin(ModelAdmin):
    list_display = ("token", "order_item", "download_count", "max_downloads", "expires_at", "revoked")
    list_filter = ("revoked",)
    search_fields = ("token", "order_item__order__email")
    readonly_fields = ("token", "order_item", "download_count")
