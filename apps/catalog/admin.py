from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeNumericFilter

from apps.downloads.models import ProductFile

from .models import Category, Framework, Product


class ProductFileInline(TabularInline):
    model = ProductFile
    extra = 0
    fields = ("title", "file", "version", "is_active")


@admin.register(Framework)
class FrameworkAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("title", "category", "format", "price", "is_active", "is_featured", "updated_at")
    list_filter = ("is_active", "is_featured", "category", "format", "frameworks", ("price", RangeNumericFilter))
    list_filter_submit = True
    list_editable = ("is_active", "is_featured")
    search_fields = ("title", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("frameworks",)
    inlines = [ProductFileInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "frameworks", "format")}),
        ("Content", {"fields": ("short_description", "description", "whats_included", "image")}),
        ("Pricing", {"fields": ("price", "compare_at_price", "currency")}),
        ("Visibility", {"fields": ("is_active", "is_featured")}),
        ("SEO", {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
    )
