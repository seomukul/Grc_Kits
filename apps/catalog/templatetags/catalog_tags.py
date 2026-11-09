from django import template

from apps.core.models import SiteSettings

register = template.Library()


@register.inclusion_tag("catalog/_badges.html", takes_context=True)
def product_badges(context, product):
    s = context.get("site_settings") or SiteSettings.load()
    return {
        "is_new": product.is_new(s),
        "is_bestseller": product.is_bestseller(s),
        "is_bundle": product.is_bundle,
        "on_sale": bool(product.compare_at_price and product.compare_at_price > product.price),
    }
