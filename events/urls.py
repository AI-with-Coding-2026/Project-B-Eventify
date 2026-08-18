from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list_view, name="event_list"),
    path("new/", views.event_create_view, name="event_create"),
    path("<int:pk>/edit/", views.event_update_view, name="event_update"),
    path("<int:pk>/delete/", views.event_delete_view, name="event_delete"),
]
