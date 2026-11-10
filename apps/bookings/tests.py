import time
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.bookings import slots
from apps.bookings.emails import manage_token
from apps.bookings.models import AvailabilityRule, BlockedDate, Booking, BookingSettings

DHAKA = ZoneInfo("Asia/Dhaka")
# A fixed "now": Monday 2 Nov 2026, 09:00 Dhaka.
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=DHAKA)


def at(day, hh, mm=0):
    return datetime(2026, 11, day, hh, mm, tzinfo=DHAKA).astimezone(dt_timezone.utc)


class SlotTests(TestCase):
    def setUp(self):
        self.s = BookingSettings.load()
        self.s.rules.all().delete()
        self.s.timezone = "Asia/Dhaka"
        self.s.duration_minutes, self.s.buffer_minutes, self.s.min_notice_hours, self.s.max_days_ahead = 30, 15, 12, 30
        self.s.save()
        # Mon/Tue 10:00-12:00 => 10:00, 10:45, 11:30 (ends exactly at 12:00)
        for wd in (0, 1):
            AvailabilityRule.objects.create(settings=self.s, weekday=wd, start_time="10:00", end_time="12:00")

    def free(self, day):
        return [x.astimezone(DHAKA).strftime("%H:%M") for x in
                slots.free_slots(at(day, 0), at(day, 23, 59), self.s, now=NOW)]

    def test_rules_duration_and_buffer(self):
        self.assertEqual(self.free(3), ["10:00", "10:45", "11:30"])  # Tuesday
        self.assertEqual(self.free(4), [])                  # Wednesday: no rule

    def test_min_notice_hides_too_soon(self):
        # Monday 2 Nov 10:00 is only 1h after NOW (< 12h notice).
        self.assertEqual(self.free(2), [])

    def test_blocked_date_and_existing_booking_with_buffer(self):
        BlockedDate.objects.create(date=datetime(2026, 11, 9).date())
        self.assertEqual(self.free(9), [])
        Booking.objects.create(name="A", email="a@x.com", start=at(3, 10), end=at(3, 10, 30))
        # 10:00-10:30 booked + 15 min buffer: 10:45 is still fine.
        self.assertEqual(self.free(3), ["10:45", "11:30"])
        Booking.objects.create(name="B", email="b@x.com", start=at(3, 11), end=at(3, 11, 30))
        self.assertEqual(self.free(3), [])  # 10:45 ends 11:15 (+15 buffer hits 11:00); 11:30 within buffer of 11:30 end
        Booking.objects.filter(email__in=["a@x.com", "b@x.com"]).update(status="cancelled")
        self.assertEqual(self.free(3), ["10:00", "10:45", "11:30"])

    def test_daily_limit(self):
        self.s.daily_limit = 1
        self.s.save()
        Booking.objects.create(name="A", email="a@x.com", start=at(3, 10), end=at(3, 10, 30))
        self.assertEqual(self.free(3), [])

    def test_visitor_timezone_shifts_days(self):
        # Tuesday 10:00 Dhaka = Monday 23:00 in New York (UTC-5).
        ny = slots.slots_for_visitor_day(datetime(2026, 11, 2).date(), "America/New_York", self.s, now=NOW)
        self.assertIn(at(3, 10), ny)
        self.assertIn(datetime(2026, 11, 2).date(), slots.available_days(2026, 11, "America/New_York", self.s, now=NOW))

    def test_bad_timezone_falls_back_to_utc(self):
        self.assertEqual(str(slots.visitor_tz("Mars/Olympus")), "UTC")

    def test_database_blocks_double_booking(self):
        from django.db import IntegrityError, transaction

        Booking.objects.create(name="A", email="a@x.com", start=at(3, 10), end=at(3, 10, 30))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(name="B", email="b@x.com", start=at(3, 10), end=at(3, 10, 30))


class BookingFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        s = BookingSettings.load()
        s.min_notice_hours = 0
        s.meeting_link = "https://meet.example.com/abc"
        s.save()
        self.slot = slots.free_slots(timezone.now(), timezone.now() + timedelta(days=14), s)[0]

    def post(self, start=None, **extra):
        data = {"name": "Ann", "email": "Ann@Example.com", "notes": "Scope", "start": (start or self.slot).isoformat(),
                "tz": "Europe/London", "ts": signing.dumps(time.time() - 30, salt="form-ts"), **extra}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("bookings:book"), data)

    def test_widget_endpoints(self):
        local = self.slot.astimezone(ZoneInfo("Europe/London"))
        resp = self.client.get(reverse("bookings:month"), {"tz": "Europe/London", "month": local.strftime("%Y-%m")})
        self.assertContains(resp, local.strftime("%-d"))
        resp = self.client.get(reverse("bookings:day"), {"tz": "Europe/London", "date": local.date().isoformat()})
        self.assertContains(resp, local.strftime("%H:%M"))
        resp = self.client.get(reverse("bookings:book"), {"tz": "Europe/London", "start": self.slot.isoformat()})
        self.assertContains(resp, "Your selected time")

    def test_booking_created_emails_and_invite(self):
        resp = self.post()
        self.assertContains(resp, "You're booked")
        b = Booking.objects.get()
        self.assertEqual((b.email, b.status, b.visitor_timezone, b.meeting_link),
                         ("ann@example.com", "confirmed", "Europe/London", "https://meet.example.com/abc"))
        self.assertEqual(b.end - b.start, timedelta(minutes=30))
        self.assertEqual(len(mail.outbox), 2)
        visitor, owner = mail.outbox
        self.assertEqual(visitor.to, ["ann@example.com"])
        self.assertIn("(Europe/London)", visitor.body)
        self.assertEqual(visitor.attachments[0][2], "text/calendar")
        self.assertIn("DTSTART:" + b.start.strftime("%Y%m%dT%H%M%SZ"), visitor.attachments[0][1])
        self.assertEqual(owner.reply_to, ["ann@example.com"])
        self.assertIn("(Asia/Dhaka)", owner.body)

    def test_slot_taken_and_unavailable_times_rejected(self):
        self.post()
        resp = self.post(email="other@x.com")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(Booking.objects.count(), 1)
        resp = self.post(start=self.slot + timedelta(minutes=7), email="odd@x.com")  # not a real slot
        self.assertEqual(resp.status_code, 409)

    def test_spam_and_rate_limit(self):
        resp = self.post(website="http://spam")
        self.assertFalse(Booking.objects.exists())
        self.assertContains(resp, "Spam detected")
        free = slots.free_slots(timezone.now(), timezone.now() + timedelta(days=30))
        for i, start in enumerate(free[:6]):
            self.post(start=start, email=f"p{i}@x.com")
        self.assertEqual(Booking.objects.count(), 4)

    def test_pending_mode(self):
        s = BookingSettings.load()
        s.auto_confirm = False
        s.save()
        self.post()
        self.assertEqual(Booking.objects.get().status, "pending")
        self.assertIn("Request received", mail.outbox[0].subject)

    def test_visitor_manage_and_cancel(self):
        self.post()
        b = Booking.objects.get()
        url = reverse("bookings:manage", args=[manage_token(b)])
        self.assertContains(self.client.get(url), "Cancel this call")
        ics = self.client.get(reverse("bookings:invite", args=[manage_token(b)]))
        self.assertEqual(ics["Content-Type"], "text/calendar")
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url, {"action": "cancel"})
        b.refresh_from_db()
        self.assertEqual(b.status, "cancelled")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("METHOD:CANCEL", mail.outbox[0].attachments[0][1])
        self.assertIn(self.slot, slots.free_slots(self.slot, self.slot + timedelta(minutes=1)))  # free again
        self.assertEqual(self.client.get(reverse("bookings:manage", args=["forged"])).status_code, 404)

    def test_email_failure_does_not_break_booking(self):
        with mock.patch("apps.bookings.emails.EmailMessage.send", side_effect=OSError("smtp down")):
            resp = self.post()
        self.assertContains(resp, "You're booked")

    @override_settings(ADMIN_2FA_REQUIRED=False)
    def test_admin_confirm_and_cancel(self):
        s = BookingSettings.load()
        s.auto_confirm = False
        s.save()
        self.post()
        b = Booking.objects.get()
        owner = get_user_model().objects.create_superuser("o", "o@x.com", "pw")
        self.client.force_login(owner)
        self.assertEqual(self.client.get(reverse("admin:bookings_booking_changelist") + "?when=upcoming").status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:bookings_bookingsettings_changelist"), follow=True).status_code, 200)
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("admin:bookings_booking_changelist"), {"action": "confirm", "_selected_action": [b.pk]})
        b.refresh_from_db()
        self.assertEqual(b.status, "confirmed")
        self.assertIn("Confirmed", mail.outbox[0].subject)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("admin:bookings_booking_changelist"), {"action": "cancel", "_selected_action": [b.pk]})
        b.refresh_from_db()
        self.assertEqual(b.status, "cancelled")

    def test_contact_page_shows_widget_and_service_preselect(self):
        from django.core.management import call_command

        call_command("seed_content", verbosity=0)
        resp = self.client.get(reverse("pages:contact") + "?service=vapt")
        self.assertContains(resp, 'id="book"')
        self.assertContains(resp, "Free 30-minute discovery call")
        self.assertContains(resp, 'data-service="')
        s = BookingSettings.load()
        s.is_enabled = False
        s.save()
        self.assertNotContains(self.client.get(reverse("pages:contact")), 'id="booking-month"')
