from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from apps.bookings.models import BookingSettings
from apps.core.models import SiteSettings
from apps.core.spam import rate_limited

from .emails import notify_owner
from .forms import InquiryForm
from .models import Service


class ServiceListView(ListView):
    template_name = "services/service_list.html"
    context_object_name = "services"
    queryset = Service.objects.filter(is_active=True)


def service_detail(request, slug):
    service = get_object_or_404(Service.objects.prefetch_related("faqs", "frameworks"), slug=slug, is_active=True)
    return render(
        request,
        "services/service_detail.html",
        {
            "service": service,
            "form": InquiryForm(show_service=False),
            "site_settings": SiteSettings.load(),
            "booking_enabled": BookingSettings.load().is_enabled,
            "others": Service.objects.filter(is_active=True).exclude(pk=service.pk)[:3],
        },
    )


def handle_inquiry(request, *, service=None, source="service", template="services/_inquiry_form.html", extra=None):
    """Shared by service pages and the contact page. Returns the form partial or a thank-you partial."""
    form = InquiryForm(request.POST, request.FILES, show_service=service is None)
    ctx = {"service": service, **(extra or {})}
    if not form.is_valid():
        return render(request, template, {**ctx, "form": form})
    if rate_limited(f"inquiry:{request.META.get('REMOTE_ADDR', '')}", limit=5):
        form.add_error(None, "Too many messages from your connection. Please try again later or email us.")
        return render(request, template, {**ctx, "form": form})
    inquiry = form.save(commit=False)
    if service is not None:
        inquiry.service = service
    inquiry.source = source
    inquiry.save()
    notify_owner(inquiry)
    return render(request, "services/_inquiry_done.html", {"inquiry": inquiry, **ctx})


@require_POST
def submit_inquiry(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return handle_inquiry(request, service=service)
