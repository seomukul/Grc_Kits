from django.urls import path

from . import exports, views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-export/<slug:report>.csv", exports.export, name="export"),
]
