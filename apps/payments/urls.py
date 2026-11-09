from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("success/", views.checkout_success, name="success"),
    path("cancel/", views.checkout_cancel, name="cancel"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("<slug:slug>/", views.create_checkout_session, name="create"),
]
