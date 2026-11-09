from django.conf import settings
from django.core.mail import mail_admins
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .forms import InquiryForm
from .models import Service


class ServiceListView(ListView):
    template_name = "services/service_list.html"
    context_object_name = "services"
    queryset = Service.objects.filter(is_active=True)


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(request, "services/service_detail.html", {"service": service, "form": InquiryForm()})


@require_POST
def submit_inquiry(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    form = InquiryForm(request.POST)
    if not form.is_valid():
        return render(request, "services/_inquiry_form.html", {"form": form, "service": service})
    inquiry = form.save(commit=False)
    inquiry.service = service
    inquiry.save()
    mail_admins(f"New inquiry: {service}", f"{inquiry.name} <{inquiry.email}>\n\n{inquiry.message}", fail_silently=True)
    return render(request, "services/_inquiry_done.html", {"inquiry": inquiry})
