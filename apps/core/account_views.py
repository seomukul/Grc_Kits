from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET

from apps.orders.models import Order
from apps.orders.services import claim_guest_orders

from . import magic_link
from .forms import MagicLinkForm

RATE_LIMIT = 5  # requests per email per hour


def _rate_limited(email, ip):
    keys = [f"magic:{email}", f"magic-ip:{ip}"]
    for key in keys:
        count = cache.get_or_set(key, 0, 3600)
        if count >= RATE_LIMIT * (4 if key.startswith("magic-ip") else 1):
            return True
    for key in keys:
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, 3600)
    return False


def _get_or_create_customer(email):
    """Existing user, or a new passwordless account if this email has bought something."""
    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    if user:
        return user
    if not Order.objects.filter(email__iexact=email, status=Order.Status.PAID).exists():
        return None
    user = User(username=email[:150], email=email)
    user.set_unusable_password()
    user.save()
    return user


def login_request(request):
    """Ask for an email and send a sign-in link. Same response whether or not the email is known."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    form = MagicLinkForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if not _rate_limited(email, request.META.get("REMOTE_ADDR", "")):
            user = _get_or_create_customer(email)
            if user:
                _send_link(request, user, next_url)
        return render(request, "account/link_sent.html", {"email": email})
    return render(request, "account/login.html", {"form": form, "next": next_url})


def _send_link(request, user, next_url):
    url = request.build_absolute_uri(reverse("account:verify", args=[magic_link.make_token(user)]))
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        url += f"?next={next_url}"
    body = render_to_string(
        "account/email/magic_link.txt",
        {"url": url, "minutes": magic_link.MAX_AGE // 60, "SITE_NAME": settings.SITE_NAME},
    )
    send_mail(f"Your {settings.SITE_NAME} sign-in link", body, None, [user.email])


@require_GET
def verify(request, token):
    user = magic_link.user_from_token(token)
    if user is None:
        return render(request, "account/link_invalid.html", status=400)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    claim_guest_orders(user)
    next_url = request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard:home")
