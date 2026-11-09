from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("<slug:slug>/submit/", views.submit_review, name="submit"),
]
