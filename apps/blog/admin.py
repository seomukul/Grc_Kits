from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import BlogCategory, MediaAsset, Post, PostAttachment, Tag


class PostAttachmentInline(TabularInline):
    model = PostAttachment
    extra = 0
    fields = ("title", "file", "order")


@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    list_display = ("__str__", "slug", "parent", "order", "post_count")
    list_editable = ("order",)
    list_filter = ("parent",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    @display(description="Posts")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ("preview", "title", "url", "created_at")
    search_fields = ("title",)
    readonly_fields = ("url",)

    @display(description="Image")
    def preview(self, obj):
        return format_html('<img src="{}" style="height:40px;border-radius:4px">', obj.file.url) if obj.file else "–"

    @display(description="URL to paste into the editor")
    def url(self, obj):
        return obj.file.url if obj.file else "Save first"


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ("title", "category", "author", "show_status", "published_at", "is_featured")
    list_filter = ("status", "category", "tags", "is_featured")
    list_editable = ("is_featured",)
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags", "frameworks", "related_products")
    autocomplete_fields = ("category",)
    date_hierarchy = "published_at"
    inlines = [PostAttachmentInline]
    actions = ["publish_now"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "tags", "author")}),
        ("Publishing", {"fields": ("status", "published_at", "is_featured"),
                        "description": "Scheduled posts go live automatically at the publish time."}),
        ("Content", {"fields": ("excerpt", "cover_image", "body")}),
        ("Calls to action", {"fields": ("related_products", "related_service", "frameworks")}),
        ("SEO", {"classes": ("collapse",), "fields": ("meta_title", "meta_description", "canonical_url", "og_image")}),
    )

    @display(description="Status", label={"published": "success", "scheduled": "info", "draft": "warning"})
    def show_status(self, obj):
        return obj.status

    def view_on_site(self, obj):
        return obj.get_absolute_url()

    @action(description="Publish now")
    def publish_now(self, request, queryset):
        n = queryset.update(status=Post.Status.PUBLISHED, published_at=timezone.now())
        messages.success(request, f"Published {n} post(s).")

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
