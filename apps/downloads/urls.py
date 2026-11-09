from django.urls import path

from . import views

app_name = "downloads"

urlpatterns = [
    path("<uuid:token>/", views.entitlement_detail, name="entitlement"),
    path("<uuid:token>/file/<int:file_id>/", views.download_file, name="file"),
]
