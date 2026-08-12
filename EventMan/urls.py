from django.urls import path

from . import views


urlpatterns = [
    path(
        'organizer/events/',
        views.organizer_event_list,
        name='organizer_event_list'
    ),

    path(
        'organizer/events/create/',
        views.create_event,
        name='create_event'
    ),

    path(
        'organizer/events/<int:event_id>/edit/',
        views.edit_event,
        name='edit_event'
    ),

    path(
        'organizer/events/<int:event_id>/delete/',
        views.delete_event,
        name='delete_event'
    ),
]