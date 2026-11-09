from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Page


class StaticViewSitemap(Sitemap):
    priority = 0.5

    def items(self):
        named = ["pages:home", "catalog:list", "services:list", "blog:list"]
        return named + list(Page.objects.filter(is_published=True))

    def location(self, item):
        return item.get_absolute_url() if isinstance(item, Page) else reverse(item)
