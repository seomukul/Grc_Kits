from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from django.contrib import messages
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from unfold.decorators import action, display

from .models import User
from .roles import EDITOR, ensure_roles

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("email", "username", "company", "is_staff", "role", "two_factor", "date_joined")
    actions = ["make_editor", "reset_two_factor"]

    @display(description="Role")
    def role(self, obj):
        if obj.is_superuser:
            return "Owner"
        if obj.groups.filter(name=EDITOR).exists():
            return "Editor"
        return "Staff" if obj.is_staff else "Customer"

    @display(description="2FA", boolean=True)
    def two_factor(self, obj):
        return TOTPDevice.objects.filter(user=obj, confirmed=True).exists() if obj.is_staff else None

    @action(description="Make Editor (blog only staff access)")
    def make_editor(self, request, queryset):
        group = ensure_roles()
        for user in queryset.filter(is_superuser=False):
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            user.groups.add(group)
        messages.success(request, "Selected users can now sign in to the admin and manage the blog.")

    @action(description="Reset two-factor (user sets it up again at next login)")
    def reset_two_factor(self, request, queryset):
        for user in queryset:
            for device in devices_for_user(user, confirmed=None):
                device.delete()
        messages.success(request, f"Two-factor reset for {queryset.count()} user(s).")
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
        ("Checkout", {"fields": ("stripe_invoices", "abandoned_cart_emails", "abandoned_cart_delay_hours")}),
        ("Contact & social", {"fields": ("contact_email", "response_time_note", "booking_url", "linkedin_url", "facebook_url", "x_url", "youtube_url")}),
        ("Newsletter lead magnet", {"fields": ("lead_magnet_title", "lead_magnet_file")}),
        ("Analytics & tracking", {
            "fields": ("ga4_measurement_id", "search_console_verification", "meta_pixel_id", "linkedin_partner_id"),
            "description": "Tracking scripts load only after a visitor clicks Accept on the cookie banner.",
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect

        return redirect("admin:core_sitesettings_change", SiteSettings.load().pk)
