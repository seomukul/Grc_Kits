from django.shortcuts import render
from django.views.decorators.http import require_POST

from .forms import SubscribeForm
from .models import Subscriber


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid() and not form.cleaned_data["website"]:
        Subscriber.objects.update_or_create(
            email=form.cleaned_data["email"].lower(),
            defaults={
                "source": form.cleaned_data["source"],
                "is_active": True,
                "consent_ip": request.META.get("REMOTE_ADDR"),
            },
        )
        return render(request, "marketing/_subscribe_done.html")
    return render(request, "marketing/_subscribe_form.html", {"form": form}, status=422 if not request.htmx else 200)
