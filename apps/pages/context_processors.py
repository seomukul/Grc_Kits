from .models import Page


def footer_pages(request):
    return {"footer_pages": Page.objects.filter(is_published=True, show_in_footer=True).only("title", "slug")}
