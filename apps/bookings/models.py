import uuid
import zoneinfo

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel

TIMEZONE_CHOICES = sorted((tz, tz) for tz in zoneinfo.available_timezones() if "/" in tz and not tz.startswith("Etc/"))


class BookingSettings(models.Model):
    """Singleton: how consultation calls can be booked."""

    is_enabled = models.BooleanField(default=True, help_text="Show the booking calendar on the site.")
    title = models.CharField(max_length=80, default="Free 30-minute discovery call")
    description = models.CharField(
        max_length=250, blank=True,
        default="Tell us where you are with your compliance project and we'll suggest the fastest route to audit-ready.",
    )
    timezone = models.CharField(max_length=64, choices=TIMEZONE_CHOICES, default="Asia/Dhaka",
                                help_text="Your timezone. Availability below is in this timezone.")
    duration_minutes = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(10), MaxValueValidator(240)])
    buffer_minutes = models.PositiveSmallIntegerField(default=15, help_text="Free time kept after each call.")
    min_notice_hours = models.PositiveSmallIntegerField(default=12, help_text="Earliest a call can be booked from now.")
    max_days_ahead = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(1), MaxValueValidator(180)])
    daily_limit = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Max calls per day. Blank = no limit.")
    meeting_link = models.URLField(blank=True, help_text="Your Google Meet / Zoom / Teams link, sent with every booking.")
    auto_confirm = models.BooleanField(
        default=True, help_text="Off: bookings wait for you to confirm them in the admin before the invite is final.",
    )
    notify_email = models.EmailField(blank=True, help_text="Where new bookings are sent. Blank = Site settings contact email.")

    class Meta:
        verbose_name = verbose_name_plural = "booking settings"

    def __str__(self):
        return "Booking settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def tz(self):
        return zoneinfo.ZoneInfo(self.timezone)


class AvailabilityRule(models.Model):
    """A weekly window when calls can start, e.g. Sunday 10:00–17:00 (in the settings timezone)."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    settings = models.ForeignKey(BookingSettings, on_delete=models.CASCADE, related_name="rules")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name = "weekly availability"

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})


class BlockedDate(models.Model):
    """Days off: holidays, travel, conferences."""

    date = models.DateField(unique=True)
    reason = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} {self.reason}".strip()


class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    ACTIVE = [Status.PENDING, Status.CONFIRMED]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED, db_index=True)

    name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    service = models.ForeignKey("services.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings")
    notes = models.TextField("what would you like to discuss?", blank=True)
    visitor_timezone = models.CharField(max_length=64, default="UTC")
    meeting_link = models.URLField(blank=True)
    cancelled_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["start"]
        constraints = [
            # Database-level guard against two active bookings at the same start time.
            models.UniqueConstraint(fields=["start"], condition=Q(status__in=["pending", "confirmed"]),
                                    name="one_active_booking_per_slot"),
        ]

    def __str__(self):
        return f"{self.name} – {self.start:%Y-%m-%d %H:%M} UTC"

    @property
    def short_ref(self):
        return str(self.reference)[:8].upper()

    @property
    def is_active(self):
        return self.status in self.ACTIVE

    def local_start(self, tz_name=None):
        return self.start.astimezone(zoneinfo.ZoneInfo(tz_name or self.visitor_timezone))
