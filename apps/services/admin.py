from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Service, ServiceInquiry


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ("title", "starting_price", "is_active", "order")
    list_editable = ("is_active", "order")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("frameworks",)


@admin.register(ServiceInquiry)
class ServiceInquiryAdmin(ModelAdmin):
    list_display = ("name", "email", "company", "service", "status", "created_at")
    list_filter = ("status", "service")
    list_editable = ("status",)
    search_fields = ("name", "email", "company", "message")
