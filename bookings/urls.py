from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("book/", views.book, name="book"),
    path("book/confirmed/<str:ref>/", views.confirmed, name="confirmed"),
    path("book/<str:ref>.ics", views.ics, name="ics"),
    path("api/slots/", views.api_slots, name="api_slots"),
]
