from django.contrib.sitemaps import Sitemap

from .models import Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.listed()

    def lastmod(self, obj):
        return obj.updated_at
