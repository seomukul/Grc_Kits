from django.urls import path

from . import admin_views, views

app_name = "downloads"

# <signed> is "<entitlement uuid>:<timestamp>:<signature>" from django.core.signing.TimestampSigner.
urlpatterns = [
    path("admin/presign-upload/", admin_views.presign_upload, name="presign_upload"),
    path("<str:signed>/", views.entitlement_detail, name="entitlement"),
    path("<str:signed>/file/<int:file_id>/", views.download_file, name="file"),
]
