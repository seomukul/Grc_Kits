from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Post


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ("title", "author", "status", "published_at")
    list_filter = ("status", "frameworks")
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("frameworks", "related_products")
    date_hierarchy = "published_at"
    fieldsets = (
        (None, {"fields": ("title", "slug", "author", "status", "published_at")}),
        ("Content", {"fields": ("excerpt", "body", "cover_image")}),
        ("Relations", {"fields": ("frameworks", "related_products")}),
        ("SEO", {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
