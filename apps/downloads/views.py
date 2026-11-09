from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.orders.models import Order

from .models import Entitlement


def _get_entitlement(token):
    return get_object_or_404(
        Entitlement.objects.select_related("order_item__order", "order_item__product"),
        token=token,
        order_item__order__status=Order.Status.PAID,
    )


@require_GET
def entitlement_detail(request, token):
    """Landing page listing the files a buyer can download. The token is the secret."""
    ent = _get_entitlement(token)
    files = ent.product.files.filter(is_active=True)
    return render(request, "downloads/entitlement.html", {"entitlement": ent, "files": files})


@require_GET
def download_file(request, token, file_id):
    ent = _get_entitlement(token)
    if not ent.is_usable:
        raise Http404("This download link has expired or reached its limit.")
    product_file = get_object_or_404(ent.product.files, pk=file_id, is_active=True)

    Entitlement.objects.filter(pk=ent.pk).update(download_count=F("download_count") + 1)
    filename = product_file.file.name.rsplit("/", 1)[-1]
    response = FileResponse(product_file.file.open("rb"), as_attachment=True, filename=filename)
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex"
    return response
