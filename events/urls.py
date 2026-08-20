from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("login/", views.OrganizerLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="events:login"), name="logout"),
    path("", views.HomeView.as_view(), name="home"),              # CHANGED
    path("my-events/", views.EventListView.as_view(), name="event_list"),  # CHANGED
    path("browse/", views.PublicEventBrowseView.as_view(), name="browse"),
    path("events/<int:pk>/book/", views.BookEventView.as_view(), name="book_event"),   # ADD
    path("my-bookings/", views.MyBookingsView.as_view(), name="my_bookings"),           # ADD
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_edit"),
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),
]