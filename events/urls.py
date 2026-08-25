from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.event_list,
        name="event_list",
    ),

    path(
        "browse/",
        views.attendee_event_list,
        name="attendee_event_list",
    ),

    path(
        "create/",
        views.event_create,
        name="event_create",
    ),

    path(
        "<int:pk>/edit/",
        views.event_edit,
        name="event_edit",
    ),

    path(
        "<int:pk>/delete/",
        views.event_delete,
        name="event_delete",
    ),

    path(
        "dashboard/",
        views.organizer_dashboard,
        name="organizer_dashboard",
    ),
]