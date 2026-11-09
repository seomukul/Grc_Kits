from .models import Page


def footer_pages(request):
    from apps.core.models import SiteSettings

    return {
        "footer_pages": Page.objects.filter(is_published=True, show_in_footer=True).only("title", "slug"),
        "site_settings": SiteSettings.load(),
    }
