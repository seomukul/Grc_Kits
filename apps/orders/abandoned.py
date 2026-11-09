"""One reminder email for checkouts that were started but never paid.

Runs from cron (`send_abandoned_cart_emails`). Off unless Site settings → abandoned cart emails is on.
"""

from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.marketing.models import Subscriber

from .models import Order

SALT = "cart-restore"
WINDOW_HOURS = 48
COOLDOWN_DAYS = 7


def restore_url(order):
    return settings.SITE_URL + reverse("orders:cart_restore", args=[signing.dumps(str(order.number), salt=SALT)])


def candidates(now=None):
    s = SiteSettings.load()
    now = now or timezone.now()
    newest = now - timedelta(hours=s.abandoned_cart_delay_hours)
    oldest = now - timedelta(hours=WINDOW_HOURS)
    qs = (
        Order.objects.filter(
            status__in=[Order.Status.PENDING, Order.Status.CANCELLED],
            created_at__gte=oldest, created_at__lte=newest, reminder_sent_at__isnull=True,
        )
        .exclude(email="")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    seen = set()
    for order in qs:
        email = order.email.lower()
        if email in seen:
            continue
        seen.add(email)
        if Order.objects.filter(email__iexact=email, status=Order.Status.PAID, paid_at__gte=order.created_at).exists():
            continue  # they bought after all
        if Order.objects.filter(email__iexact=email, reminder_sent_at__gte=now - timedelta(days=COOLDOWN_DAYS)).exists():
            continue
        if Subscriber.objects.filter(email__iexact=email, is_active=False).exists():
            continue  # opted out of marketing
        yield order


def send_reminders(now=None):
    if not SiteSettings.load().abandoned_cart_emails:
        return 0
    sent = 0
    for order in list(candidates(now)):
        body = render_to_string(
            "orders/email/abandoned.txt",
            {"order": order, "url": restore_url(order), "SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL},
        )
        EmailMessage(f"You left something in your {settings.SITE_NAME} cart", body, to=[order.email]).send()
        Order.objects.filter(pk=order.pk).update(reminder_sent_at=timezone.now())
        sent += 1
    return sent
