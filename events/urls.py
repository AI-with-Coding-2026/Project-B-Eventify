from django.urls import path

from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),

    path(
        '<int:pk>/book/',
        views.book_ticket,
        name='book_ticket',
    ),

    path(
        'my-tickets/',
        views.my_tickets,
        name='my_tickets',
    ),

    path(
        'organizer/',
        views.organizer_event_list,
        name='organizer_event_list',
    ),

    path(
        'organizer/create/',
        views.event_create,
        name='event_create',
    ),

    path(
        'organizer/<int:pk>/edit/',
        views.event_edit,
        name='event_edit',
    ),

    path(
        'organizer/<int:pk>/delete/',
        views.event_delete,
        name='event_delete',
    ),

    path(
        'categories/',
        views.category_list,
        name='category_list',
    ),

    path(
        'categories/create/',
        views.category_create,
        name='category_create',
    ),

    path(
        'categories/<int:pk>/edit/',
        views.category_update,
        name='category_update',
    ),

    path(
        'categories/<int:pk>/delete/',
        views.category_delete,
        name='category_delete',
    ),
]