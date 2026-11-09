from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.blog.sitemaps import BlogCategorySitemap, PostSitemap
from apps.catalog.sitemaps import ProductSitemap
from apps.pages.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
    "blog": PostSitemap,
    "blog-categories": BlogCategorySitemap,
}

urlpatterns = [
    path("admin/2fa/", include("apps.core.two_factor_urls")),
    path("admin/", admin.site.urls),
    path("account/", include("apps.core.account_urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("kits/", include("apps.catalog.urls")),
    path("checkout/", include("apps.payments.urls")),
    path("", include("apps.orders.urls")),
    path("downloads/", include("apps.downloads.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("newsletter/", include("apps.marketing.urls")),
    path("blog/", include("apps.blog.urls")),
    path("services/", include("apps.services.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    # Keep pages last: it owns "/" and the "/<slug>/" catch-all for CMS pages.
    path("", include("apps.pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns = [path("__debug__/", include("debug_toolbar.urls"))] + urlpatterns
