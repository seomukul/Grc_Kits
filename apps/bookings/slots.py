"""Work out which call start times are free.

Availability rules are wall-clock times in the owner's timezone. Slots are returned as aware UTC
datetimes; the UI converts them to the visitor's timezone for display.
"""

import zoneinfo
from datetime import date, datetime, timedelta, timezone as dt_timezone
from functools import lru_cache

from django.utils import timezone

from .models import AvailabilityRule, BlockedDate, Booking, BookingSettings

UTC = dt_timezone.utc


@lru_cache(maxsize=1)
def _valid_timezones():
    return zoneinfo.available_timezones()


def visitor_tz(name):
    """A safe ZoneInfo for whatever the browser reported (falls back to UTC)."""
    return zoneinfo.ZoneInfo(name) if name in _valid_timezones() else zoneinfo.ZoneInfo("UTC")


def booking_window(settings=None, now=None):
    """(earliest start, latest start) a visitor may book."""
    s = settings or BookingSettings.load()
    now = now or timezone.now()
    return now + timedelta(hours=s.min_notice_hours), now + timedelta(days=s.max_days_ahead)


def _candidates_for_owner_day(day, settings, rules):
    """All slot starts on an owner-local calendar day, ignoring existing bookings."""
    tz, step = settings.tz, timedelta(minutes=settings.duration_minutes + settings.buffer_minutes)
    length = timedelta(minutes=settings.duration_minutes)
    for rule in rules:
        if rule.weekday != day.weekday():
            continue
        start = datetime.combine(day, rule.start_time, tzinfo=tz)
        end = datetime.combine(day, rule.end_time, tzinfo=tz)
        while start + length <= end:
            yield start.astimezone(UTC)
            start += step


def free_slots(range_start, range_end, settings=None, now=None):
    """Free slot starts (UTC) within [range_start, range_end)."""
    s = settings or BookingSettings.load()
    if not s.is_enabled:
        return []
    earliest, latest = booking_window(s, now)
    lo, hi = max(range_start, earliest), min(range_end, latest)
    if lo >= hi:
        return []

    rules = list(AvailabilityRule.objects.filter(settings=s))
    blocked = set(BlockedDate.objects.values_list("date", flat=True))
    buffer = timedelta(minutes=s.buffer_minutes)
    length = timedelta(minutes=s.duration_minutes)
    busy = list(
        Booking.objects.filter(status__in=Booking.ACTIVE, start__lt=hi + length + buffer, end__gt=lo - length - buffer)
        .values_list("start", "end")
    )
    per_day = {}
    if s.daily_limit:
        for start, _ in Booking.objects.filter(status__in=Booking.ACTIVE, start__gte=lo - timedelta(days=1),
                                               start__lt=hi + timedelta(days=1)).values_list("start", "end"):
            d = start.astimezone(s.tz).date()
            per_day[d] = per_day.get(d, 0) + 1

    out = []
    day = lo.astimezone(s.tz).date()
    last_day = hi.astimezone(s.tz).date()
    while day <= last_day:
        if day not in blocked and (not s.daily_limit or per_day.get(day, 0) < s.daily_limit):
            for slot in _candidates_for_owner_day(day, s, rules):
                if not (lo <= slot < hi):
                    continue
                slot_end = slot + length
                if any(slot < b_end + buffer and b_start < slot_end + buffer for b_start, b_end in busy):
                    continue
                out.append(slot)
        day += timedelta(days=1)
    return sorted(out)


def slots_for_visitor_day(day: date, tz_name, settings=None, now=None):
    """Free slots that fall on `day` in the visitor's own timezone."""
    tz = visitor_tz(tz_name)
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz).astimezone(UTC)
    return free_slots(start, start + timedelta(days=1), settings, now)


def available_days(year, month, tz_name, settings=None, now=None):
    """Set of dates (visitor timezone) in a month that have at least one free slot."""
    tz = visitor_tz(tz_name)
    first = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    start = datetime.combine(first, datetime.min.time(), tzinfo=tz).astimezone(UTC)
    end = datetime.combine(nxt, datetime.min.time(), tzinfo=tz).astimezone(UTC)
    return {slot.astimezone(tz).date() for slot in free_slots(start, end, settings, now)}


def is_free(start, settings=None, now=None):
    s = settings or BookingSettings.load()
    return start in free_slots(start, start + timedelta(minutes=1), s, now)
