from django.shortcuts import get_object_or_404, render

from apps.blog.models import Post
from apps.catalog.models import Framework, Product
from apps.services.models import Service

from .models import Page


def home(request):
    ctx = {
        "featured_products": Product.objects.listed().filter(is_featured=True).select_related("category")[:6],
        "frameworks": Framework.objects.all()[:12],
        "services": Service.objects.filter(is_active=True)[:3],
        "latest_posts": Post.objects.published()[:3],
    }
    return render(request, "pages/home.html", ctx)


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "pages/page.html", {"page": page})
