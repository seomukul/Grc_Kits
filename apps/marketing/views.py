from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings
from apps.core.spam import rate_limited

from .emails import send_welcome_email
from .forms import SubscribeForm
from .models import Subscriber


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid() and not form.cleaned_data["website"]:
        if rate_limited(f"subscribe:{request.META.get('REMOTE_ADDR', '')}", limit=10):
            return render(request, "marketing/_subscribe_done.html", {"lead_magnet_url": ""})
        subscriber, created = Subscriber.objects.update_or_create(
            email=form.cleaned_data["email"].lower(),
            defaults={
                "source": form.cleaned_data["source"],
                "is_active": True,
                "consent_ip": request.META.get("REMOTE_ADDR"),
            },
        )
        s = SiteSettings.load()
        lead_magnet_url = request.build_absolute_uri(s.lead_magnet_file.url) if s.lead_magnet_file else ""
        if created:
            send_welcome_email(subscriber, lead_magnet_url, s)
        return render(
            request,
            "marketing/_subscribe_done.html",
            {"lead_magnet_url": lead_magnet_url, "lead_magnet_title": s.lead_magnet_title},
        )
    return render(request, "marketing/_subscribe_form.html", {"form": form}, status=422 if not request.htmx else 200)
