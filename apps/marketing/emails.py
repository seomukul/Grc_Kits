from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_welcome_email(subscriber, lead_magnet_url, site_settings):
    body = render_to_string(
        "marketing/email/welcome.txt",
        {
            "lead_magnet_url": lead_magnet_url,
            "lead_magnet_title": site_settings.lead_magnet_title,
            "SITE_URL": settings.SITE_URL,
            "SITE_NAME": settings.SITE_NAME,
        },
    )
    send_mail(f"Welcome to {settings.SITE_NAME}", body, None, [subscriber.email], fail_silently=True)
