from django.contrib.sitemaps import Sitemap

from .models import BlogCategory, Post


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Post.objects.published().filter(canonical_url="")

    def lastmod(self, obj):
        return obj.updated_at


class BlogCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.4

    def items(self):
        return BlogCategory.objects.all()
