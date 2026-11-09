from django.conf import settings
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string

from apps.core.models import SiteSettings

from .models import Entitlement


def notify_buyers_of_update(product_file):
    """Email everyone who owns this file's product that a new version is available.

    Each buyer gets a fresh signed link. Returns the number of emails sent.
    """
    version = product_file.latest_version
    if version is None:
        return 0
    entitlements = (
        Entitlement.objects.filter(product=product_file.product, revoked=False, order_item__order__status="paid")
        .select_related("order_item__order")
        .order_by("order_item__order__email", "-created_at")
    )
    ttl = SiteSettings.load().download_link_ttl_hours
    seen, messages = set(), []
    for ent in entitlements:
        email = ent.order.email
        if not email or email in seen:
            continue
        seen.add(email)
        body = render_to_string(
            "downloads/email/new_version.txt",
            {
                "product": product_file.product,
                "product_file": product_file,
                "version": version,
                "link": settings.SITE_URL + ent.get_absolute_url(),
                "SITE_NAME": settings.SITE_NAME,
                "ttl_hours": ttl,
            },
        )
        subject = f"Update available: {product_file.product.title} v{version.version}"
        messages.append((subject, body, None, [email]))
    send_mass_mail(messages, fail_silently=False)
    return len(messages)
