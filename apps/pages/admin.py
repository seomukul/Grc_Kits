from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Page


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ("title", "slug", "is_published", "show_in_footer", "updated_at")
    list_editable = ("is_published", "show_in_footer")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "body")
