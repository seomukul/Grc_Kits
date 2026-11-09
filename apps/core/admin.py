from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import User

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("email", "username", "company", "is_staff", "date_joined")
    search_fields = ("email", "username", "company")
    fieldsets = BaseUserAdmin.fieldsets + (("GRCkits", {"fields": ("company", "stripe_customer_id")}),)
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "email", "password1", "password2")}),
    )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


from .models import SiteSettings  # noqa: E402


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("Downloads", {"fields": ("download_limit", "download_link_ttl_hours")}),
        ("License tiers", {"fields": ("team_price_multiplier", "organization_price_multiplier", "team_max_users")}),
        ("Storefront badges", {"fields": ("new_badge_days", "bestseller_min_sales")}),
        ("Checkout", {"fields": ("stripe_invoices",)}),
        ("Contact & social", {"fields": ("contact_email", "response_time_note", "booking_url", "linkedin_url", "facebook_url", "x_url", "youtube_url")}),
        ("Newsletter lead magnet", {"fields": ("lead_magnet_title", "lead_magnet_file")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect

        return redirect("admin:core_sitesettings_change", SiteSettings.load().pk)
