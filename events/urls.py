from django.urls import path
from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),

    path(
        "categories/create/",
        views.category_create,
        name="category_create",
    ),

    path(
        "mine/",
        views.my_events,
        name="my_events",
    ),

    path(
        "create/",
        views.create_event,
        name="create_event",
    ),

    path(
        "<int:pk>/",
        views.event_detail,
        name="event_detail",
    ),

    path(
        "<int:pk>/book/",
        views.book_event,
        name="book_event",
    ),

    path(
        "<int:pk>/edit/",
        views.edit_event,
        name="edit_event",
    ),

    path(
        "<int:pk>/delete/",
        views.delete_event,
        name="delete_event",
    ),
    # Edit/update an existing category
    # URL example: /events/categories/1/edit/
    path(
        'categories/<int:pk>/edit/',
        views.category_update,
        name='category_update',
    ),
]
