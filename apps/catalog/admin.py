from django.contrib import admin, messages
from django.utils.text import slugify
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import RangeNumericFilter
from unfold.decorators import action, display

from apps.core.models import SiteSettings
from apps.downloads.models import ProductFile

from .models import Category, Framework, Product, ProductFAQ, ProductImage, ProductLicense


class ProductLicenseInline(TabularInline):
    model = ProductLicense
    extra = 0
    fields = ("tier", "price", "is_active", "effective")
    readonly_fields = ("effective",)
    verbose_name_plural = "Extra license tiers (Single user always uses the main price)"

    @display(description="Effective price")
    def effective(self, obj):
        return f"${obj.effective_price()}" if obj.pk else "–"


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "alt", "order")


class ProductFAQInline(TabularInline):
    model = ProductFAQ
    extra = 0
    fields = ("question", "answer", "order")


class ProductFileInline(TabularInline):
    model = ProductFile
    extra = 0
    fields = ("title", "order", "is_active", "latest")
    readonly_fields = ("latest",)
    show_change_link = True
    verbose_name_plural = "Downloadable files (open a file to upload versions)"

    @display(description="Latest version")
    def latest(self, obj):
        v = obj.latest_version if obj.pk else None
        return f"v{v.version}" if v else "no upload yet"


@admin.register(Framework)
class FrameworkAdmin(ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("title", "category", "product_type", "price", "show_status", "is_featured", "updated_at")
    list_filter = (
        "status", "is_featured", "product_type", "category", "frameworks", ("price", RangeNumericFilter),
    )
    list_filter_submit = True
    list_editable = ("is_featured",)
    search_fields = ("title", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("frameworks", "bundle_items")
    inlines = [ProductLicenseInline, ProductImageInline, ProductFileInline, ProductFAQInline]
    actions = ["publish", "unpublish", "duplicate"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "frameworks", "product_type")}),
        ("Status", {"fields": ("status", "publish_at", "is_featured")}),
        ("Content", {"fields": ("short_description", "description", "whats_included", "system_requirements")}),
        ("Media & preview", {"fields": ("image", "preview_video_url", "sample_file")}),
        ("Pricing", {"fields": ("price", "compare_at_price", "currency")}),
        (
            "Bundle",
            {
                "classes": ("collapse",),
                "description": "Only for products of type Bundle: buyers get the files of every product below.",
                "fields": ("bundle_items",),
            },
        ),
        ("SEO", {"classes": ("collapse",), "fields": ("meta_title", "meta_description", "og_image")}),
    )

    @display(
        description="Status",
        label={"published": "success", "draft": "info", "hidden": "warning", "scheduled": "primary"},
    )
    def show_status(self, obj):
        return obj.status

    @action(description="Publish selected products")
    def publish(self, request, queryset):
        n = queryset.update(status=Product.Status.PUBLISHED)
        messages.success(request, f"Published {n} product(s).")

    @action(description="Move selected products to Draft")
    def unpublish(self, request, queryset):
        n = queryset.update(status=Product.Status.DRAFT)
        messages.success(request, f"Moved {n} product(s) to Draft.")

    @action(description="Duplicate selected products (as Draft)")
    def duplicate(self, request, queryset):
        for original in queryset.prefetch_related("frameworks", "bundle_items", "licenses"):
            frameworks = list(original.frameworks.all())
            bundle_items = list(original.bundle_items.all())
            licenses = list(original.licenses.all())
            copy = original
            copy.pk = None
            copy.id = None
            copy.title = f"{original.title} (copy)"
            base = slugify(copy.title)[:200]
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            copy.slug = slug
            copy.status = Product.Status.DRAFT
            copy.is_featured = False
            copy._state.adding = True
            copy.save()
            copy.frameworks.set(frameworks)
            copy.bundle_items.set(bundle_items)
            for lic in licenses:
                ProductLicense.objects.create(product=copy, tier=lic.tier, price=lic.price, is_active=lic.is_active)
        messages.success(request, f"Duplicated {queryset.count()} product(s). Files are not copied.")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        s = SiteSettings.load()
        if "price" in form.base_fields:
            form.base_fields["price"].help_text = (
                f"Single-user price. Team defaults to ×{s.team_price_multiplier}, "
                f"Organization to ×{s.organization_price_multiplier} (Site settings)."
            )
        return form
