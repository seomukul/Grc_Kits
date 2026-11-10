import calendar
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.core import signing
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from apps.core.spam import rate_limited

from . import emails, slots
from .forms import BookingForm
from .ics import build_ics
from .models import Booking, BookingSettings


def _tz(request):
    name = request.GET.get("tz") or request.POST.get("tz") or "UTC"
    return name if name in slots._valid_timezones() else "UTC"


@require_GET
def month(request):
    """HTMX: month grid with bookable days highlighted (in the visitor's timezone)."""
    s = BookingSettings.load()
    tz_name = _tz(request)
    tz = slots.visitor_tz(tz_name)
    today = timezone.now().astimezone(tz).date()
    try:
        year, mon = map(int, request.GET.get("month", "").split("-"))
        first = date(year, mon, 1)
    except ValueError:
        first = today.replace(day=1)
    earliest, latest = slots.booking_window(s)
    first = max(first, earliest.astimezone(tz).date().replace(day=1))
    available = slots.available_days(first.year, first.month, tz_name, s)
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    return render(request, "bookings/_month.html", {
        "first": first, "weeks": weeks, "available": available, "today": today, "tz": tz_name,
        "prev_month": prev_month if prev_month >= earliest.astimezone(tz).date().replace(day=1) else None,
        "next_month": next_month if next_month <= latest.astimezone(tz).date() else None,
        "selected": request.GET.get("date", ""),
    })


@require_GET
def day(request):
    """HTMX: free times on one day, shown in the visitor's timezone."""
    tz_name = _tz(request)
    try:
        d = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        raise Http404
    tz = slots.visitor_tz(tz_name)
    times = [(s, s.astimezone(tz)) for s in slots.slots_for_visitor_day(d, tz_name)]
    return render(request, "bookings/_day.html", {"day": d, "times": times, "tz": tz_name,
                                                   "settings": BookingSettings.load()})


def book(request):
    """GET (HTMX): details form for a chosen slot. POST: create the booking."""
    s = BookingSettings.load()
    tz_name = _tz(request)
    if request.method == "GET":
        start = parse_datetime(request.GET.get("start", ""))
        if not start or not slots.is_free(start, s):
            return render(request, "bookings/_taken.html", {"tz": tz_name}, status=409)
        service = request.GET.get("service")
        form = BookingForm(initial={"start": start.isoformat(), "tz": tz_name,
                                    "service": service if service and service.isdigit() else None})
        return render(request, "bookings/_form.html", {"form": form, "start": start,
                                                        "local": start.astimezone(slots.visitor_tz(tz_name)), "settings": s})

    form = BookingForm(request.POST)
    if not form.is_valid():
        start = parse_datetime(request.POST.get("start", "")) or timezone.now()
        return render(request, "bookings/_form.html", {"form": form, "start": start,
                                                        "local": start.astimezone(slots.visitor_tz(tz_name)), "settings": s})
    if rate_limited(f"booking:{request.META.get('REMOTE_ADDR', '')}", limit=4):
        form.add_error(None, "Too many bookings from your connection. Please email us instead.")
        return render(request, "bookings/_form.html", {"form": form, "start": form.cleaned_data["start"], "settings": s,
                                                        "local": form.cleaned_data["start"].astimezone(slots.visitor_tz(tz_name))})
    start = form.cleaned_data["start"].astimezone(slots.UTC)
    try:
        with transaction.atomic():
            if not slots.is_free(start, s):
                raise IntegrityError("slot taken")
            booking = form.save(commit=False)
            booking.start = start
            booking.end = start + timedelta(minutes=s.duration_minutes)
            booking.visitor_timezone = form.cleaned_data["tz"]
            booking.meeting_link = s.meeting_link
            booking.status = Booking.Status.CONFIRMED if s.auto_confirm else Booking.Status.PENDING
            booking.email = booking.email.lower()
            booking.save()
    except IntegrityError:
        return render(request, "bookings/_taken.html", {"tz": tz_name}, status=409)
    transaction.on_commit(lambda: emails.booking_created(booking))
    return render(request, "bookings/_done.html", {"b": booking, "local": booking.local_start(), "settings": s,
                                                    "token": emails.manage_token(booking)})


def _from_token(token):
    try:
        ref = signing.loads(token, salt=emails.SALT, max_age=60 * 60 * 24 * 365)
    except signing.BadSignature:
        raise Http404
    return get_object_or_404(Booking, reference=ref)


def manage(request, token):
    """Visitor's own page (link in their email): see the booking, download the invite, cancel."""
    booking = _from_token(token)
    if request.method == "POST" and request.POST.get("action") == "cancel" and booking.is_active:
        if booking.start <= timezone.now():
            messages.error(request, "This call has already started.")
        else:
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_reason = "Cancelled by visitor"
            booking.save(update_fields=["status", "cancelled_reason", "updated_at"])
            transaction.on_commit(lambda: emails.booking_cancelled(booking, by_visitor=True))
            messages.success(request, "Your call has been cancelled. You can book another time below.")
        return redirect("bookings:manage", token=token)
    return render(request, "bookings/manage.html", {"b": booking, "local": booking.local_start(), "token": token,
                                                     "settings": BookingSettings.load()})


@require_GET
def invite(request, token):
    booking = _from_token(token)
    response = HttpResponse(build_ics(booking, cancelled=not booking.is_active), content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="grckits-call-{booking.short_ref}.ics"'
    return response
