from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from . import emails
from .models import AvailabilityRule, BlockedDate, Booking, BookingSettings


class AvailabilityRuleInline(TabularInline):
    model = AvailabilityRule
    extra = 0
    fields = ("weekday", "start_time", "end_time")
    verbose_name_plural = "Weekly availability (in your timezone). Add several rows for split days, e.g. 10–13 and 15–18."


@admin.register(BookingSettings)
class BookingSettingsAdmin(ModelAdmin):
    inlines = [AvailabilityRuleInline]
    fieldsets = (
        (None, {"fields": ("is_enabled", "title", "description")}),
        ("Schedule", {"fields": ("timezone", "duration_minutes", "buffer_minutes", "min_notice_hours",
                                 "max_days_ahead", "daily_limit")}),
        ("Meeting & notifications", {"fields": ("meeting_link", "auto_confirm", "notify_email")}),
    )

    def has_add_permission(self, request):
        return not BookingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return redirect("admin:bookings_bookingsettings_change", BookingSettings.load().pk)


@admin.register(BlockedDate)
class BlockedDateAdmin(ModelAdmin):
    list_display = ("date", "reason")
    date_hierarchy = "date"


class UpcomingFilter(admin.SimpleListFilter):
    title = "when"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return [("upcoming", "Upcoming"), ("past", "Past")]

    def queryset(self, request, queryset):
        if self.value() == "upcoming":
            return queryset.filter(start__gte=timezone.now())
        if self.value() == "past":
            return queryset.filter(start__lt=timezone.now())
        return queryset


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ("when", "name", "email", "company", "service", "show_status")
    list_filter = (UpcomingFilter, "status", "service")
    search_fields = ("name", "email", "company", "notes")
    date_hierarchy = "start"
    readonly_fields = ("reference", "when", "their_time", "visitor_timezone", "created_at")
    fieldsets = (
        (None, {"fields": ("status", "when", "their_time", "meeting_link", "cancelled_reason")}),
        ("Visitor", {"fields": ("name", "email", "company", "phone", "service", "notes", "visitor_timezone")}),
        ("Meta", {"classes": ("collapse",), "fields": ("reference", "start", "end", "created_at")}),
    )
    actions = ["confirm", "cancel"]
    actions_detail = ["confirm_detail", "cancel_detail"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service")

    def changelist_view(self, request, extra_context=None):
        # Default to upcoming calls, but only for plain page views (never redirect action POSTs).
        if request.method == "GET" and not request.GET:
            return redirect(request.path + "?when=upcoming")
        return super().changelist_view(request, extra_context)

    @display(description="When (your time)", ordering="start")
    def when(self, obj):
        s = BookingSettings.load()
        return f"{obj.local_start(s.timezone):%a %d %b %Y, %H:%M} ({s.timezone})" if obj.start else "–"

    @display(description="Their time")
    def their_time(self, obj):
        return f"{obj.local_start():%a %d %b, %H:%M} ({obj.visitor_timezone})" if obj.start else "–"

    @display(description="Status", label={"confirmed": "success", "pending": "warning", "cancelled": "danger",
                                          "completed": "info"})
    def show_status(self, obj):
        return obj.status

    def _confirm(self, request, qs):
        n = 0
        for b in qs.filter(status=Booking.Status.PENDING):
            b.status = Booking.Status.CONFIRMED
            b.save(update_fields=["status", "updated_at"])
            transaction.on_commit(lambda b=b: emails.booking_confirmed(b))
            n += 1
        messages.success(request, f"Confirmed {n} booking(s); visitors were emailed.")

    def _cancel(self, request, qs):
        n = 0
        for b in qs.filter(status__in=Booking.ACTIVE):
            b.status = Booking.Status.CANCELLED
            b.cancelled_reason = b.cancelled_reason or "Cancelled by GRCkits"
            b.save(update_fields=["status", "cancelled_reason", "updated_at"])
            transaction.on_commit(lambda b=b: emails.booking_cancelled(b, by_visitor=False))
            n += 1
        messages.success(request, f"Cancelled {n} booking(s); visitors were emailed and the time is free again.")

    @action(description="Confirm selected (email visitor)")
    def confirm(self, request, queryset):
        self._confirm(request, queryset)

    @action(description="Cancel selected (email visitor)")
    def cancel(self, request, queryset):
        self._cancel(request, queryset)

    @action(description="Confirm")
    def confirm_detail(self, request, object_id):
        self._confirm(request, Booking.objects.filter(pk=object_id))
        return redirect("admin:bookings_booking_change", object_id)

    @action(description="Cancel booking")
    def cancel_detail(self, request, object_id):
        self._cancel(request, Booking.objects.filter(pk=object_id))
        return redirect("admin:bookings_booking_change", object_id)
