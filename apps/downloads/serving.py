from django.conf import settings
from django.http import FileResponse, HttpResponseRedirect

PRESIGNED_URL_SECONDS = 300


def serve_private_file(version):
    """Hand a private file to the buyer.

    R2: redirect to a presigned URL valid for a few minutes, so the bytes never pass through Django.
    Local disk: stream the file from Django.
    """
    filename = version.filename
    if settings.USE_R2:
        url = version.file.storage.url(
            version.file.name,
            parameters={"ResponseContentDisposition": f'attachment; filename="{filename}"'},
            expire=PRESIGNED_URL_SECONDS,
        )
        response = HttpResponseRedirect(url)
    else:
        response = FileResponse(version.file.open("rb"), as_attachment=True, filename=filename)
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex"
    return response
