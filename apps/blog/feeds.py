from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from .models import Post


class LatestPostsFeed(Feed):
    title = f"{settings.SITE_NAME} blog"
    link = "/blog/"
    description = "GRC, ISO 27001, risk management and compliance insights."

    def items(self):
        return Post.objects.published().select_related("author")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_author_name(self, item):
        return item.author.get_full_name() if item.author else settings.SITE_NAME

    def item_categories(self, item):
        return [t.name for t in item.tags.all()]


class AtomFeed(LatestPostsFeed):
    feed_type = Atom1Feed
    subtitle = LatestPostsFeed.description
