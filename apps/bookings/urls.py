from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("month/", views.month, name="month"),
    path("day/", views.day, name="day"),
    path("new/", views.book, name="book"),
    path("manage/<str:token>/", views.manage, name="manage"),
    path("manage/<str:token>/invite.ics", views.invite, name="invite"),
]
