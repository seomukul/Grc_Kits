"""Minimal iCalendar (.ics) file so the call lands in any calendar app."""

from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone


def _esc(text):
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fmt(dt):
    return dt.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(booking, cancelled=False):
    domain = settings.SITE_URL.split("//")[-1].split("/")[0]
    summary = f"{settings.SITE_NAME} call: {booking.service or 'Discovery call'}"
    description = f"Booking {booking.short_ref}\n{booking.notes}".strip()
    if booking.meeting_link:
        description += f"\nJoin: {booking.meeting_link}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{settings.SITE_NAME}//Bookings//EN",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancelled else 'PUBLISH'}",
        "BEGIN:VEVENT",
        f"UID:{booking.reference}@{domain}",
        f"DTSTAMP:{_fmt(timezone.now())}",
        f"DTSTART:{_fmt(booking.start)}",
        f"DTEND:{_fmt(booking.end)}",
        f"SUMMARY:{_esc(summary)}",
        f"DESCRIPTION:{_esc(description)}",
        f"LOCATION:{_esc(booking.meeting_link or 'Online (link to follow)')}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED' if booking.status == 'confirmed' else 'TENTATIVE'}",
        "SEQUENCE:1" if cancelled else "SEQUENCE:0",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
