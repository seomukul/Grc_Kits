from django.conf import settings
from django.core.mail import EmailMessage

from apps.core.models import SiteSettings


def notify_owner(inquiry):
    """Email the lead to the owner. Reply-To is the customer so the owner can just hit reply."""
    s = SiteSettings.load()
    lines = [
        f"Name: {inquiry.name}",
        f"Email: {inquiry.email}",
        f"Company: {inquiry.company or '–'}",
        f"Service: {inquiry.service or 'General question'}",
        f"Source: {inquiry.source}",
        "",
        inquiry.message,
        "",
        f"Attachment: {'yes, see admin' if inquiry.attachment else 'none'}",
        f"Admin: {settings.SITE_URL}/admin/services/serviceinquiry/{inquiry.pk}/change/",
    ]
    EmailMessage(
        subject=f"New lead: {inquiry.service or 'General question'} – {inquiry.name}",
        body="\n".join(lines),
        to=[s.contact_email],
        reply_to=[inquiry.email],
    ).send(fail_silently=True)
