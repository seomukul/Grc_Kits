from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_welcome_email(subscriber, lead_magnet_url, site_settings):
    body = render_to_string(
        "marketing/email/welcome.txt",
        {
            "lead_magnet_url": lead_magnet_url,
            "lead_magnet_title": site_settings.lead_magnet_title,
            "SITE_URL": settings.SITE_URL,
            "SITE_NAME": settings.SITE_NAME,
            "unsubscribe_url": settings.SITE_URL + subscriber.get_unsubscribe_url(),
        },
    )
    unsubscribe = settings.SITE_URL + subscriber.get_unsubscribe_url()
    EmailMessage(
        f"Welcome to {settings.SITE_NAME}", body, to=[subscriber.email],
        headers={"List-Unsubscribe": f"<{unsubscribe}>"},
    ).send(fail_silently=True)
