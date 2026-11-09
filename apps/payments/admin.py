from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import StripeEvent


@admin.register(StripeEvent)
class StripeEventAdmin(ModelAdmin):
    list_display = ("type", "event_id", "processed_at")
    list_filter = ("type",)
    search_fields = ("event_id",)
    readonly_fields = ("event_id", "type", "payload", "processed_at")

    def has_add_permission(self, request):
        return False
