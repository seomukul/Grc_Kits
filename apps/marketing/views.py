from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings
from apps.core.spam import rate_limited

from . import esp
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
                "unsubscribed_at": None,
                "consent_ip": request.META.get("REMOTE_ADDR"),
            },
        )
        transaction.on_commit(lambda: esp.sync(subscriber))
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


def unsubscribe(request, token):
    """GET shows a confirm button (so link scanners can't unsubscribe people); POST unsubscribes."""
    try:
        email = signing.loads(token, salt="newsletter-unsubscribe", max_age=60 * 60 * 24 * 365 * 3)
    except signing.BadSignature:
        return render(request, "marketing/unsubscribe.html", {"invalid": True}, status=400)
    subscriber = get_object_or_404(Subscriber, email=email)
    if request.method == "POST":
        subscriber.is_active = False
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=["is_active", "unsubscribed_at"])
        transaction.on_commit(lambda: esp.sync(subscriber))
        return render(request, "marketing/unsubscribe.html", {"done": True, "email": email})
    return render(request, "marketing/unsubscribe.html", {"email": email, "token": token})
