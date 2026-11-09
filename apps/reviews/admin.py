from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import Review


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("product", "user", "rating", "title", "is_verified_purchase", "is_approved", "created_at")
    list_filter = ("is_approved", "is_verified_purchase", "rating")
    list_editable = ("is_approved",)
    search_fields = ("title", "body", "product__title", "user__email")
    actions = ["approve"]

    @action(description="Approve selected reviews")
    def approve(self, request, queryset):
        queryset.update(is_approved=True)
