from django.urls import path

from . import views

app_name = "services"

urlpatterns = [
    path("", views.ServiceListView.as_view(), name="list"),
    path("<slug:slug>/", views.service_detail, name="detail"),
    path("<slug:slug>/inquire/", views.submit_inquiry, name="inquire"),
]
