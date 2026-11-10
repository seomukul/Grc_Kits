from django.contrib import admin
from django.shortcuts import redirect
from unfold.admin import ModelAdmin

from .models import AboutProfile, FAQItem, HeroSlide, HomeSection, Page, Testimonial, TrustItem


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ("title", "slug", "is_published", "show_in_footer", "footer_order", "updated_at")
    list_editable = ("is_published", "show_in_footer", "footer_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")


@admin.register(HomeSection)
class HomeSectionAdmin(ModelAdmin):
    list_display = ("__str__", "title", "is_enabled", "order", "item_limit", "period")
    list_editable = ("title", "is_enabled", "order", "item_limit", "period")
    list_display_links = ("__str__",)
    readonly_fields = ("key",)
    fields = (
        "key", "eyebrow", "title", "subtitle", "is_enabled", "order", "item_limit", "period",
        "content", "button_label", "button_url",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    list_display = ("headline", "button_url", "is_active", "order")
    list_editable = ("is_active", "order")


@admin.register(TrustItem)
class TrustItemAdmin(ModelAdmin):
    list_display = ("text", "icon", "order")
    list_editable = ("icon", "order")


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ("name", "role", "rating", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "quote")


@admin.register(FAQItem)
class FAQItemAdmin(ModelAdmin):
    list_display = ("question", "topic", "show_on_home", "show_on_products", "order")
    list_editable = ("show_on_home", "show_on_products", "order")
    list_filter = ("topic",)


@admin.register(AboutProfile)
class AboutProfileAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return not AboutProfile.objects.exists()

    def changelist_view(self, request, extra_context=None):
        obj = AboutProfile.load()
        if obj:
            return redirect("admin:pages_aboutprofile_change", obj.pk)
        return redirect("admin:pages_aboutprofile_add")
