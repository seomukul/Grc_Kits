from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("<uuid:number>/", views.order_detail, name="detail"),
]
