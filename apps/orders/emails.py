from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.core.models import SiteSettings


def send_order_confirmation(order):
    if not order.email:
        return
    entitlements = [e for item in order.items.all() for e in item.entitlements.all()]
    body = render_to_string(
        "orders/email/confirmation.txt",
        {
            "order": order,
            "entitlements": entitlements,
            "ttl_hours": SiteSettings.load().download_link_ttl_hours,
            "SITE_URL": settings.SITE_URL,
            "SITE_NAME": settings.SITE_NAME,
        },
    )
    send_mail(f"Your {settings.SITE_NAME} order {order.short_number}", body, None, [order.email])
