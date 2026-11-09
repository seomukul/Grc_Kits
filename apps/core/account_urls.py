from django.urls import path

from . import account_views

app_name = "account"

urlpatterns = [
    path("login/", account_views.login_request, name="login"),
    path("login/<str:token>/", account_views.verify, name="verify"),
]
