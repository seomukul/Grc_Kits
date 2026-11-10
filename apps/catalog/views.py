from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from django.utils.html import strip_tags

from apps.core.models import SiteSettings
from apps.core.richtext import render_body
from apps.pages.models import FAQItem
from apps.downloads.models import Entitlement
from apps.reviews.forms import ReviewForm

from .models import Category, Framework, Product

SORT_OPTIONS = {
    "featured": ("Featured", ["-is_featured", "title"]),
    "newest": ("Newest", ["-created_at"]),
    "popular": ("Most popular", ["-total_sales", "-created_at"]),
    "price_asc": ("Price: low to high", ["price"]),
    "price_desc": ("Price: high to low", ["-price"]),
    "rating": ("Top rated", ["-avg_rating", "-review_count"]),
}

RATING_FILTER = Q(reviews__is_approved=True)

# Descriptions longer than this start collapsed with a "Read more" button.
LONG_DESCRIPTION_WORDS = 250


def _decimal(value):
    try:
        return Decimal(value) if value not in (None, "") else None
    except InvalidOperation:
        return None


class ProductListView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        params = self.request.GET
        qs = (
            Product.objects.listed()
            .select_related("category")
            .with_recent_sales()
            .with_total_sales()
            .annotate(
                avg_rating=Avg("reviews__rating", filter=RATING_FILTER),
                review_count=Count("reviews", filter=RATING_FILTER, distinct=True),
            )
        )
        self.category = None
        if slug := self.kwargs.get("slug"):
            self.category = get_object_or_404(Category, slug=slug)
            qs = qs.filter(category=self.category)
        if fw := params.get("framework"):
            qs = qs.filter(frameworks__slug=fw)
        if ptype := params.get("type"):
            qs = qs.filter(product_type=ptype)
        if (min_price := _decimal(params.get("min_price"))) is not None:
            qs = qs.filter(price__gte=min_price)
        if (max_price := _decimal(params.get("max_price"))) is not None:
            qs = qs.filter(price__lte=max_price)
        if (min_rating := _decimal(params.get("rating"))) is not None:
            qs = qs.filter(avg_rating__gte=min_rating)
        if q := params.get("q", "").strip():
            qs = qs.filter(
                Q(title__icontains=q) | Q(short_description__icontains=q) | Q(frameworks__name__icontains=q)
            )
        self.sort = params.get("sort") if params.get("sort") in SORT_OPTIONS else "featured"
        return qs.order_by(*SORT_OPTIONS[self.sort][1]).distinct()

    def get_template_names(self):
        # HTMX filter/search/sort requests only need the results partial.
        if self.request.htmx and not self.request.htmx.boosted:
            return ["catalog/_product_grid.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx.update(
            category=self.category,
            categories=Category.objects.all(),
            frameworks=Framework.objects.all(),
            product_types=Product.ProductType.choices,
            sort_options=[(k, v[0]) for k, v in SORT_OPTIONS.items()],
            current_sort=self.sort,
            filters=self.request.GET,
            querystring=params.urlencode(),
            site_settings=SiteSettings.load(),
        )
        return ctx


class ProductDetailView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return (
            Product.objects.purchasable()
            .select_related("category")
            .prefetch_related("frameworks", "images", "bundle_items", "licenses", "faqs")
            .with_recent_sales()
            .annotate(
                avg_rating=Avg("reviews__rating", filter=RATING_FILTER),
                review_count=Count("reviews", filter=RATING_FILTER, distinct=True),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        site_settings = SiteSettings.load()
        user = self.request.user
        is_buyer = user.is_authenticated and Entitlement.objects.filter(
            order_item__order__user=user, order_item__order__status="paid", product=product
        ).exists()
        already_reviewed = user.is_authenticated and product.reviews.filter(user=user).exists()
        description = render_body(product.description)
        words = len(strip_tags(product.description or "").split())
        ctx.update(
            description_html=description.html if words else "",
            description_long=words > LONG_DESCRIPTION_WORDS,
            site_settings=site_settings,
            license_options=product.license_options(site_settings),
            reviews=product.reviews.filter(is_approved=True).select_related("user")[:10],
            can_review=is_buyer and not already_reviewed,
            review_form=ReviewForm(),
            files=product.files.filter(is_active=True) if not product.is_bundle else [],
            related=Product.objects.listed()
            .filter(Q(frameworks__in=product.frameworks.all()) | Q(category=product.category))
            .exclude(pk=product.pk)
            .select_related("category")
            .distinct()[:3],
            bundles_including=product.included_in_bundles.listed()[:2],
            faqs=list(product.faqs.all()) + list(FAQItem.objects.filter(show_on_products=True)),
        )
        return ctx
