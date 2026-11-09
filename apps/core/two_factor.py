"""Two-factor authentication (authenticator app + backup codes) for staff using the admin.

Flow: staff log in with their password as usual, then this middleware sends them to
/admin/2fa/setup/ (first time) or /admin/2fa/verify/ until their session is OTP-verified.
"""

import base64
import io
import secrets

import qrcode
import qrcode.image.svg
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login
from django_otp import devices_for_user, match_token, user_has_device
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

EXEMPT_PREFIXES = ("/admin/login/", "/admin/logout/", "/admin/2fa/", "/admin/jsi18n/")


class StaffTwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = getattr(request, "user", None)
        if (
            settings.ADMIN_2FA_REQUIRED
            and path.startswith("/admin/")
            and not path.startswith(EXEMPT_PREFIXES)
            and user is not None
            and user.is_authenticated
            and user.is_staff
            and not user.is_verified()
        ):
            target = "otp_verify" if user_has_device(user, confirmed=True) else "otp_setup"
            return redirect(f"{reverse(target)}?next={request.get_full_path()}")
        return self.get_response(request)


class TokenForm(forms.Form):
    token = forms.CharField(
        label="6-digit code", max_length=16,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True}),
    )


def _next(request):
    nxt = request.GET.get("next") or request.POST.get("next") or "/admin/"
    return nxt if url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else "/admin/"


def _ctx(request, **extra):
    return {**admin.site.each_context(request), "next": _next(request), **extra}


def _qr_svg(uri):
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def _backup_codes(user, n=8):
    device, _ = StaticDevice.objects.get_or_create(user=user, name="backup")
    device.token_set.all().delete()
    codes = [secrets.token_hex(4) for _ in range(n)]
    for code in codes:
        StaticToken.objects.create(device=device, token=code)
    return codes


@login_required(login_url="admin:login")
def setup(request):
    user = request.user
    if not user.is_staff:
        return redirect("/")
    if user_has_device(user, confirmed=True) and not user.is_verified():
        return redirect(f"{reverse('otp_verify')}?next={_next(request)}")
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first() or TOTPDevice.objects.create(
        user=user, name="Authenticator app", confirmed=False
    )
    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["token"].strip()):
            device.confirmed = True
            device.save()
            otp_login(request, device)
            codes = _backup_codes(user)
            return render(request, "admin/2fa/backup_codes.html", _ctx(request, codes=codes, title="Save your backup codes"))
        form.add_error("token", "That code didn't match. Check your phone's time and try again.")
    return render(
        request, "admin/2fa/setup.html",
        _ctx(request, form=form, qr=_qr_svg(device.config_url), secret=device.key and base64.b32encode(bytes.fromhex(device.key)).decode(), title="Set up two-factor authentication"),
    )


@login_required(login_url="admin:login")
def verify(request):
    user = request.user
    if not user.is_staff:
        return redirect("/")
    if user.is_verified():
        return redirect(_next(request))
    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = match_token(user, form.cleaned_data["token"].strip().replace(" ", ""))
        if device is not None:
            otp_login(request, device)
            if isinstance(device, StaticDevice):
                left = device.token_set.count()
                messages.warning(request, f"You used a backup code. {left} left. Generate new ones if you're running low.")
            return redirect(_next(request))
        throttled = any(
            not d.verify_is_allowed()[0] for d in devices_for_user(user) if hasattr(d, "verify_is_allowed")
        )
        form.add_error("token", "Too many attempts. Wait a few seconds and try again." if throttled else "Invalid or expired code.")
    return render(request, "admin/2fa/verify.html", _ctx(request, form=form, title="Two-factor verification"))


@login_required(login_url="admin:login")
def new_backup_codes(request):
    if not (request.user.is_staff and request.user.is_verified()) or request.method != "POST":
        return redirect("/admin/")
    return render(request, "admin/2fa/backup_codes.html", _ctx(request, codes=_backup_codes(request.user), title="New backup codes"))
