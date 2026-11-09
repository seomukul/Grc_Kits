from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ("email", "source", "is_active", "created_at")
    list_filter = ("is_active", "source")
    search_fields = ("email",)
