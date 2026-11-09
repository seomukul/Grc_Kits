from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import Category, Framework, Product


class ProductListView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.published().select_related("category").prefetch_related("frameworks")
        self.category = None
        if slug := self.kwargs.get("slug"):
            self.category = get_object_or_404(Category, slug=slug)
            qs = qs.filter(category=self.category)
        if fw := self.request.GET.get("framework"):
            qs = qs.filter(frameworks__slug=fw)
        if q := self.request.GET.get("q", "").strip():
            qs = qs.filter(Q(title__icontains=q) | Q(short_description__icontains=q))
        return qs.distinct()

    def get_template_names(self):
        # HTMX filter/search requests only need the grid partial.
        if self.request.htmx:
            return ["catalog/_product_grid.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            category=self.category,
            categories=Category.objects.all(),
            frameworks=Framework.objects.all(),
            q=self.request.GET.get("q", ""),
            active_framework=self.request.GET.get("framework", ""),
        )
        return ctx


class ProductDetailView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return (
            Product.objects.published()
            .select_related("category")
            .prefetch_related("frameworks")
            .annotate(
                avg_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
                review_count=Count("reviews", filter=Q(reviews__is_approved=True)),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["reviews"] = self.object.reviews.filter(is_approved=True).select_related("user")[:10]
        return ctx
