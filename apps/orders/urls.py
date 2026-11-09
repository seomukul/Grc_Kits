from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("orders/<uuid:number>/", views.order_detail, name="detail"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<slug:slug>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/coupon/", views.cart_coupon, name="cart_coupon"),
]
