from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.core.models import SiteSettings

from .models import DownloadLog, Entitlement
from .serving import serve_private_file


def _resolve(signed):
    """Return (entitlement, None) or (None, reason) for a signed link."""
    ttl = SiteSettings.load().download_link_ttl_hours
    try:
        token = Entitlement.unsign(signed, max_age_hours=ttl)
    except signing.SignatureExpired:
        return None, "expired"
    except signing.BadSignature:
        raise Http404
    ent = get_object_or_404(
        Entitlement.objects.select_related("order_item__order", "product"), token=token
    )
    if not ent.is_active:
        return None, "inactive"
    return ent, None


def _unavailable(request, reason):
    return render(request, "downloads/unavailable.html", {"reason": reason}, status=410)


@require_GET
def entitlement_detail(request, signed):
    ent, reason = _resolve(signed)
    if reason:
        return _unavailable(request, reason)
    files = [
        {"file": f, "version": f.latest_version, "used": ent.downloads_used(f)}
        for f in ent.product.files.filter(is_active=True).prefetch_related("versions")
    ]
    return render(
        request,
        "downloads/entitlement.html",
        {"entitlement": ent, "files": [f for f in files if f["version"]], "signed": signed},
    )


@require_GET
def download_file(request, signed, file_id):
    ent, reason = _resolve(signed)
    if reason:
        return _unavailable(request, reason)
    product_file = get_object_or_404(ent.product.files, pk=file_id, is_active=True)
    version = product_file.latest_version
    if version is None:
        raise Http404
    if not ent.can_download(product_file):
        return _unavailable(request, "limit")

    DownloadLog.objects.create(
        entitlement=ent,
        product_file=product_file,
        version=version,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )
    return serve_private_file(version)
