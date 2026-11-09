from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.blog.models import Post
from apps.catalog.models import Category, Framework, Product
from apps.core.models import SiteSettings
from apps.marketing.forms import SubscribeForm
from apps.services.forms import InquiryForm
from apps.services.models import Service
from apps.services.views import handle_inquiry

from .models import AboutProfile, FAQItem, HeroSlide, HomeSection, Page, Testimonial, TrustItem

RATING = Q(reviews__is_approved=True)


def _products():
    return (
        Product.objects.listed()
        .select_related("category")
        .with_recent_sales()
        .annotate(avg_rating=Avg("reviews__rating", filter=RATING), review_count=Count("reviews", filter=RATING, distinct=True))
    )


def _section_items(section):
    """Data for one home section, or None to skip rendering it (nothing to show)."""
    n = section.item_limit
    key = HomeSection.Key
    if section.key == key.HERO:
        return list(HeroSlide.objects.filter(is_active=True)[:5]) or None
    if section.key == key.TRUST:
        return list(TrustItem.objects.all()) or None
    if section.key == key.FEATURED:
        return list(_products().filter(is_featured=True)[:n]) or None
    if section.key == key.TOP_SELLING:
        qs = _products()
        if section.period == HomeSection.Period.ALL_TIME:
            qs = qs.with_total_sales().filter(total_sales__gt=0).order_by("-total_sales")
        else:
            qs = qs.filter(recent_sales__gt=0).order_by("-recent_sales")
        return list(qs[:n]) or None
    if section.key == key.NEW_ARRIVALS:
        return list(_products().order_by("-created_at")[:n]) or None
    if section.key == key.BROWSE:
        frameworks = list(Framework.objects.annotate(n=Count("products", filter=Q(products__status="published"))))
        categories = list(Category.objects.annotate(n=Count("products", filter=Q(products__status="published"))))
        return {"frameworks": frameworks, "categories": categories} if frameworks or categories else None
    if section.key == key.BUNDLES:
        return list(_products().filter(product_type=Product.ProductType.BUNDLE).prefetch_related("bundle_items")[:n]) or None
    if section.key == key.SERVICES:
        return list(Service.objects.filter(is_active=True)[:n]) or None
    if section.key == key.TESTIMONIALS:
        return list(Testimonial.objects.filter(is_active=True)[:n]) or None
    if section.key == key.BLOG:
        return list(Post.objects.published()[: min(n, 3)]) or None
    if section.key == key.NEWSLETTER:
        return True
    if section.key == key.FAQ:
        return list(FAQItem.objects.filter(show_on_home=True)[:n]) or None
    return None


def home(request):
    sections = []
    for section in HomeSection.objects.filter(is_enabled=True):
        items = _section_items(section)
        if items:
            sections.append({"section": section, "items": items, "template": f"pages/home/_{section.key}.html"})
    return render(
        request,
        "pages/home.html",
        {"sections": sections, "site_settings": SiteSettings.load(), "subscribe_form": SubscribeForm()},
    )


def about(request):
    return render(
        request,
        "pages/about.html",
        {"profile": AboutProfile.load(), "services": Service.objects.filter(is_active=True)[:6]},
    )


def contact(request):
    if request.method == "POST":
        return handle_inquiry(request, source="contact", template="pages/_contact_form.html")
    initial = {}
    if slug := request.GET.get("service"):
        initial["service"] = Service.objects.filter(slug=slug, is_active=True).first()
    return render(
        request,
        "pages/contact.html",
        {"form": InquiryForm(initial=initial), "site_settings": SiteSettings.load()},
    )


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "pages/page.html", {"page": page})
