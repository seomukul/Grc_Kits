import logging

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from apps.core.models import SiteSettings

from .ics import build_ics
from .models import BookingSettings

SALT = "booking-manage"
logger = logging.getLogger(__name__)


def manage_token(booking):
    return signing.dumps(str(booking.reference), salt=SALT)


def manage_url(booking):
    return settings.SITE_URL + reverse("bookings:manage", args=[manage_token(booking)])


def _send(subject, template, to, booking, reply_to=None, cancelled=False, **extra):
    """Never let an email problem break the booking itself: log and carry on."""
    try:
        _build_and_send(subject, template, to, booking, reply_to, cancelled, **extra)
    except Exception:
        logger.exception("Booking email %s failed for %s", template, booking.short_ref)


def _build_and_send(subject, template, to, booking, reply_to, cancelled, **extra):
    s = BookingSettings.load()
    body = render_to_string(f"bookings/email/{template}.txt", {
        "b": booking, "settings": s, "local_start": booking.local_start(), "owner_start": booking.local_start(s.timezone),
        "manage_url": manage_url(booking), "SITE_NAME": settings.SITE_NAME, "SITE_URL": settings.SITE_URL, **extra,
    })
    msg = EmailMessage(subject, body, to=to, reply_to=reply_to)
    msg.attach(f"grckits-call-{booking.short_ref}.ics", build_ics(booking, cancelled=cancelled), "text/calendar")
    msg.send(fail_silently=True)


def owner_address():
    return BookingSettings.load().notify_email or SiteSettings.load().contact_email


def booking_created(booking):
    pending = booking.status == booking.Status.PENDING
    _send(f"{'Request received' if pending else 'Confirmed'}: your {settings.SITE_NAME} call", "visitor_created", [booking.email], booking)
    _send(f"New call booking: {booking.name} ({booking.local_start(BookingSettings.load().timezone):%a %d %b %H:%M})",
          "owner_created", [owner_address()], booking, reply_to=[booking.email],
          admin_url=settings.SITE_URL + reverse("admin:bookings_booking_change", args=[booking.pk]))


def booking_confirmed(booking):
    _send(f"Confirmed: your {settings.SITE_NAME} call", "visitor_confirmed", [booking.email], booking)


def booking_cancelled(booking, by_visitor):
    _send(f"Cancelled: {settings.SITE_NAME} call {booking.short_ref}", "visitor_cancelled", [booking.email], booking,
          cancelled=True, by_visitor=by_visitor)
    _send(f"Booking cancelled: {booking.name} ({booking.short_ref})", "owner_cancelled", [owner_address()], booking,
          cancelled=True, by_visitor=by_visitor)
