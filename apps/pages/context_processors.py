from .models import Page


def footer_pages(request):
    from apps.core.models import SiteSettings
    from apps.services.models import Service

    return {
        # Lazy queryset: only hits the DB on pages that render the header menu.
        "nav_services": Service.objects.filter(is_active=True).only("title", "slug", "summary", "icon"),
        "footer_pages": Page.objects.filter(is_published=True, show_in_footer=True).only("title", "slug"),
        "site_settings": SiteSettings.load(),
    }
