from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Service, ServiceFAQ, ServiceInquiry


class ServiceFAQInline(TabularInline):
    model = ServiceFAQ
    extra = 0
    fields = ("question", "answer", "order")


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ("title", "starting_price", "is_active", "order")
    list_editable = ("is_active", "order")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("frameworks",)
    inlines = [ServiceFAQInline]
    fieldsets = (
        (None, {"fields": ("title", "slug", "icon", "summary", "is_active", "order")}),
        ("Page content", {"fields": ("description", "deliverables", "process_steps", "audience")}),
        ("Pricing & CTA", {"fields": ("starting_price", "cta_label", "frameworks")}),
        ("SEO", {"classes": ("collapse",), "fields": ("meta_description",)}),
    )


@admin.register(ServiceInquiry)
class ServiceInquiryAdmin(ModelAdmin):
    list_display = ("name", "email", "company", "service", "source", "status", "created_at")
    list_filter = ("status", "service", "source")
    list_editable = ("status",)
    search_fields = ("name", "email", "company", "message")
    readonly_fields = ("name", "email", "company", "service", "message", "source", "attachment_link", "created_at")
    fields = ("status", "name", "email", "company", "service", "source", "message", "attachment_link", "created_at")

    @display(description="Attachment")
    def attachment_link(self, obj):
        if not obj.attachment:
            return "–"
        url = reverse("admin:services_inquiry_attachment", args=[obj.pk])
        return format_html('<a href="{}" class="underline">{}</a>', url, obj.attachment.name.rsplit("/", 1)[-1])

    def get_urls(self):
        return [
            path(
                "<int:pk>/attachment/",
                self.admin_site.admin_view(self.download_attachment),
                name="services_inquiry_attachment",
            )
        ] + super().get_urls()

    def download_attachment(self, request, pk):
        inquiry = get_object_or_404(ServiceInquiry, pk=pk)
        if not inquiry.attachment:
            raise Http404
        name = inquiry.attachment.name.rsplit("/", 1)[-1]
        return FileResponse(inquiry.attachment.open("rb"), as_attachment=True, filename=name)
