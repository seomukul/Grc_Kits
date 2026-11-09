import uuid

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import storages
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_POST

PRESIGN_SECONDS = 3600
MAX_UPLOAD_BYTES = 5 * 1024**3  # R2 single PUT limit is 5 GiB


@staff_member_required
@require_POST
def presign_upload(request):
    """Return a presigned PUT URL so the admin browser can upload directly to R2."""
    if not settings.USE_R2:
        return HttpResponseBadRequest("R2 is not configured.")
    filename = get_valid_filename(request.POST.get("filename", ""))[:200]
    size = int(request.POST.get("size") or 0)
    if not filename:
        return HttpResponseBadRequest("filename required")
    if size > MAX_UPLOAD_BYTES:
        return HttpResponseBadRequest("File too large.")
    content_type = request.POST.get("content_type") or "application/octet-stream"
    key = f"uploads/{uuid.uuid4().hex}/{filename}"
    storage = storages["private"]
    url = storage.bucket.meta.client.generate_presigned_url(
        "put_object",
        Params={"Bucket": storage.bucket_name, "Key": key, "ContentType": content_type},
        ExpiresIn=PRESIGN_SECONDS,
    )
    return JsonResponse({"url": url, "key": key, "content_type": content_type})
